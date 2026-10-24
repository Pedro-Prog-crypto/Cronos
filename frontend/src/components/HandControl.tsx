import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Hand, Square, TriangleAlert } from 'lucide-react';
import { getToken } from '../api';
import './hand-control.css';

// Local, bundled MediaPipe assets: webcam frames and landmarks stay on this PC.
import handsScript from '@mediapipe/hands/hands.js?url';
import packedLoader from '@mediapipe/hands/hands_solution_packed_assets_loader.js?url';
import packedData from '@mediapipe/hands/hands_solution_packed_assets.data?url';
import wasmJs from '@mediapipe/hands/hands_solution_wasm_bin.js?url';
import wasm from '@mediapipe/hands/hands_solution_wasm_bin.wasm?url';
import simdWasmJs from '@mediapipe/hands/hands_solution_simd_wasm_bin.js?url';
import simdWasm from '@mediapipe/hands/hands_solution_simd_wasm_bin.wasm?url';
import handGraph from '@mediapipe/hands/hands.binarypb?url';
import handModel from '@mediapipe/hands/hand_landmark_lite.tflite?url';

type Point = { x: number; y: number; z?: number };
type Results = { multiHandLandmarks?: Point[][]; multiHandedness?: { label?: string }[] };
type Tracker = {
  setOptions: (value: unknown) => void;
  onResults: (fn: (result: Results) => void) => void;
  initialize: () => Promise<void>;
  send: (value: { image: HTMLVideoElement }) => Promise<void>;
  close: () => Promise<void>;
};
type TrackableHand = { points: Point[]; side: string; gesture: string };
type XY = { x: number; y: number };

const connections: Array<[number, number]> = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12], [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
];
const files: Record<string, string> = {
  'hands_solution_packed_assets_loader.js': packedLoader,
  'hands_solution_packed_assets.data': packedData,
  'hands_solution_wasm_bin.js': wasmJs,
  'hands_solution_wasm_bin.wasm': wasm,
  'hands_solution_simd_wasm_bin.js': simdWasmJs,
  'hands_solution_simd_wasm_bin.wasm': simdWasm,
  'hands.binarypb': handGraph,
  'hand_landmark_lite.tflite': handModel,
};
let scriptPromise: Promise<void> | null = null;

async function loadTracker(): Promise<Tracker> {
  const target = window as typeof window & { Hands?: new (options: unknown) => Tracker };
  if (!target.Hands) {
    scriptPromise ??= new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = handsScript;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null;
        reject(new Error('Não consegui carregar o rastreador local de mãos.'));
      };
      document.head.append(script);
    });
    await scriptPromise;
  }
  if (typeof target.Hands !== 'function') throw new Error('O rastreador local de mãos não iniciou.');
  const tracker = new target.Hands({ locateFile: (name: string) => files[name] || name });
  tracker.setOptions({
    maxNumHands: 2,
    modelComplexity: 0,
    selfieMode: false,
    minDetectionConfidence: 0.52,
    minTrackingConfidence: 0.48,
  });
  return tracker;
}

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);
const extended = (points: Point[], tip: number, pip: number) =>
  distance(points[0], points[tip]) > distance(points[0], points[pip]) * 1.12;
const pinchDistance = (points: Point[], tip: number) => {
  const palmWidth = Math.max(0.025, distance(points[5], points[17]));
  return distance(points[4], points[tip]) / palmWidth;
};
const palmCenter = (points: Point[]): XY => ({
  x: (points[0].x + points[5].x + points[9].x + points[13].x + points[17].x) / 5,
  y: (points[0].y + points[5].y + points[9].y + points[13].y + points[17].y) / 5,
});

export function HandControl() {
  const [active, setActive] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [hands, setHands] = useState<TrackableHand[]>([]);
  const [cursor, setCursor] = useState<XY | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const camera = useRef<MediaStream | null>(null);
  const tracker = useRef<Tracker | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const loop = useRef<number | undefined>(undefined);
  const busy = useRef(false);
  const enabled = useRef(false);
  const leftDown = useRef(false);
  const leftCandidateAt = useRef(0);
  const rightPinched = useRef(false);
  const filterPoint = useRef({ x: 0.5, y: 0.5, rawX: 0.5, rawY: 0.5, at: 0 });
  const lastMove = useRef(0);
  const lastScroll = useRef({ y: 0, at: 0 });
  const lastRight = useRef(0);
  const twoHandZoomDistance = useRef(0);
  const lastZoom = useRef(0);
  const lastDimensions = useRef({ width: window.innerWidth, height: window.innerHeight });
  enabled.current = active;

  const send = (action: string, extra: Record<string, number> = {}) => {
    const ws = socket.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action, ...extra }));
  };
  const release = useCallback(() => {
    if (!leftDown.current) return;
    leftDown.current = false;
    leftCandidateAt.current = 0;
    try {
      if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ action: 'up' }));
    } catch { /* The websocket close handler also releases the OS button. */ }
  }, []);

  const stop = useCallback(async (message = '') => {
    enabled.current = false;
    setActive(false);
    setStarting(false);
    if (loop.current !== undefined) window.clearTimeout(loop.current);
    loop.current = undefined;
    release();
    const current = socket.current;
    socket.current = null;
    if (current && current.readyState < WebSocket.CLOSING) current.close(1000, 'Gestos desligados');
    camera.current?.getTracks().forEach((track) => track.stop());
    camera.current = null;
    if (video.current) video.current.srcObject = null;
    const model = tracker.current;
    tracker.current = null;
    if (model) await model.close().catch(() => {});
    busy.current = false;
    rightPinched.current = false;
    twoHandZoomDistance.current = 0;
    setHands([]);
    setCursor(null);
    setStatus('');
    if (message) setError(message);
  }, [release]);

  const detect = (result: Results) => {
    if (!enabled.current) return;
    const all = (result.multiHandLandmarks || []).filter((points) => points.length >= 21);
    const now = performance.now();
    const details = all.map((points, index) => {
      const indexUp = extended(points, 8, 6);
      const middleUp = extended(points, 12, 10);
      const ringUp = extended(points, 16, 14);
      const pinkyUp = extended(points, 20, 18);
      const leftPinchRatio = pinchDistance(points, 8);
      const rightPinchRatio = pinchDistance(points, 12);
      const isLeftPinch = leftPinchRatio < (leftDown.current ? 0.43 : 0.30);
      const isRightPinch = rightPinchRatio < (rightPinched.current ? 0.43 : 0.30);
      const isScroll = indexUp && middleUp && !ringUp && !pinkyUp && !isLeftPinch && !isRightPinch;
      const openPalm = indexUp && middleUp && ringUp && pinkyUp && !isLeftPinch && !isRightPinch;
      const pointPose = indexUp && !middleUp && !ringUp && !pinkyUp;
      const fist = !indexUp && !middleUp && !ringUp && !pinkyUp;
      const gesture = isLeftPinch ? 'PINÇA · ARRASTAR' : isRightPinch ? 'PINÇA · CLIQUE DIREITO'
        : isScroll ? 'DOIS DEDOS · ROLAR' : pointPose ? 'INDICADOR · CURSOR' : openPalm ? 'MÃO ABERTA · CURSOR'
          : fist ? 'PUNHO · PAUSA' : 'RASTREAMENTO';
      return {
        points,
        side: result.multiHandedness?.[index]?.label || `MÃO ${index + 1}`,
        gesture,
        leftPinch: isLeftPinch,
        rightPinch: isRightPinch,
        scroll: isScroll,
        openPalm,
        pointPose,
      };
    });
    setHands(details.map(({ points, side, gesture }) => ({ points, side, gesture })));
    if (!details.length) {
      release();
      rightPinched.current = false;
      lastScroll.current = { y: 0, at: 0 };
      twoHandZoomDistance.current = 0;
      return;
    }

    const first = details[0];
    const second = details[1];
    const bothPinching = details.length === 2 && first.leftPinch && second.leftPinch;
    if (bothPinching && second) {
      release();
      rightPinched.current = false;
      const gap = distance(palmCenter(first.points), palmCenter(second.points));
      if (twoHandZoomDistance.current && Math.abs(gap - twoHandZoomDistance.current) > 0.045 && now - lastZoom.current > 240) {
        send('zoom', { delta: Math.sign(gap - twoHandZoomDistance.current) * 120 });
        lastZoom.current = now;
        twoHandZoomDistance.current = gap;
      } else if (!twoHandZoomDistance.current) {
        twoHandZoomDistance.current = gap;
      }
      setStatus('Duas pinças · afaste ou aproxime para zoom · Esc desliga');
      return;
    }
    twoHandZoomDistance.current = 0;

    const moveCursor = first.openPalm || first.pointPose || first.leftPinch || first.rightPinch;
    if (moveCursor) {
      // Always map the index fingertip to the cursor. Adaptive smoothing
      // calms small landmark jitter while following fast movement closely.
      const tip = first.points[8];
      const target = { x: Math.min(1, Math.max(0, 1 - tip.x)), y: Math.min(1, Math.max(0, tip.y)) };
      const previous = filterPoint.current;
      const dt = previous.at ? Math.max(0.008, (now - previous.at) / 1000) : 1 / 24;
      const speed = Math.hypot(target.x - previous.rawX, target.y - previous.rawY) / dt;
      const alpha = Math.min(0.88, Math.max(0.24, 0.24 + speed * 0.14));
      const smooth = previous.at
        ? { x: previous.x + (target.x - previous.x) * alpha, y: previous.y + (target.y - previous.y) * alpha }
        : target;
      filterPoint.current = { ...smooth, rawX: target.x, rawY: target.y, at: now };
      const dimensions = lastDimensions.current;
      setCursor({ x: smooth.x * dimensions.width, y: smooth.y * dimensions.height });
      if (now - lastMove.current > 20) {
        send('move', smooth);
        lastMove.current = now;
      }
    }

    if (first.leftPinch) {
      if (!leftCandidateAt.current) leftCandidateAt.current = now;
      if (!leftDown.current && now - leftCandidateAt.current >= 90) {
        leftDown.current = true;
        send('down');
      }
    } else {
      leftCandidateAt.current = 0;
      release();
    }

    if (first.rightPinch && !rightPinched.current && now - lastRight.current > 500) {
      send('right_click');
      lastRight.current = now;
    }
    rightPinched.current = first.rightPinch;

    if (first.scroll) {
      const y = (first.points[9].y + first.points[0].y) * 0.5;
      const previous = lastScroll.current;
      if (previous.at && now - previous.at > 110 && Math.abs(y - previous.y) > 0.035) {
        send('wheel', { delta: Math.sign(previous.y - y) * 120 });
        lastScroll.current = { y, at: now };
      } else if (!previous.at || now - previous.at > 450) lastScroll.current = { y, at: now };
    } else lastScroll.current = { y: 0, at: 0 };

    const instruction = first.openPalm ? 'Indicador guia o cursor · mão aberta não clica'
      : first.pointPose ? 'Indicador aponta e move · faça pinça para selecionar/arrastar'
      : first.leftPinch ? 'Pinça indicador mantida · arraste · solte para liberar'
        : first.rightPinch ? 'Clique direito'
          : first.scroll ? 'Dois dedos · mova para rolar'
            : 'Punho ou gesto neutro · cursor pausado';
    setStatus(`${instruction} · duas pinças afastam/aproximam para zoom · Esc desliga`);
  };

  const start = async () => {
    if (active || starting) return;
    setError('');
    setStarting(true);
    setStatus('Conectando ao controle local…');
    try {
      if (!getToken()) throw new Error('Conecte o Cronos antes de ativar os gestos.');
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('A câmera precisa de permissão no navegador do Cronos.');
      const wsUrl = new URL('/gestures/control', window.location.href);
      wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(wsUrl, ['cronos-auth', getToken()]);
      socket.current = ws;
      await new Promise<void>((resolve, reject) => {
        let handshaken = false;
        const timer = window.setTimeout(() => reject(new Error('O controle do Windows não respondeu.')), 6000);
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'ready') {
            handshaken = true;
            lastDimensions.current = { width: window.innerWidth, height: window.innerHeight };
            window.clearTimeout(timer);
            resolve();
          } else if (data.type === 'unavailable') {
            window.clearTimeout(timer);
            reject(new Error(data.message || 'O controle global não está disponível.'));
          }
        };
        ws.onerror = () => { window.clearTimeout(timer); reject(new Error('Não consegui conectar o controle local do Windows.')); };
        ws.onclose = () => {
          window.clearTimeout(timer);
          if (enabled.current) void stop('O controle local foi desconectado.');
          else if (!handshaken) reject(new Error('Não foi possível autenticar o controle local do Windows.'));
        };
      });
      camera.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 320, max: 480 }, height: { ideal: 240, max: 360 }, frameRate: { ideal: 24, max: 30 } },
        audio: false,
      });
      camera.current.getVideoTracks()[0]?.addEventListener('ended', () => {
        if (enabled.current) void stop('A câmera foi desconectada. O controle por gestos foi parado.');
      }, { once: true });
      if (!video.current) throw new Error('A câmera não ficou pronta.');
      video.current.srcObject = camera.current;
      await video.current.play();
      const model = await loadTracker();
      tracker.current = model;
      model.onResults(detect);
      await model.initialize();
      lastDimensions.current = { width: window.innerWidth, height: window.innerHeight };
      enabled.current = true;
      setActive(true);
      setStarting(false);
      setError('');
      setStatus('A ponta do indicador move · pinça indicador clica/arrasta · pinça médio clica com botão direito · dois dedos rolam · duas pinças fazem zoom');
      const tick = async () => {
        if (!enabled.current) return;
        const source = video.current;
        if (source && source.readyState >= 2 && !busy.current) {
          busy.current = true;
          try { await model.send({ image: source }); }
          catch { void stop('A leitura da câmera falhou. Pare e inicie o controle novamente.'); return; }
          finally { busy.current = false; }
        }
        // Adaptive loop: process the next frame as soon as inference completes,
        // while leaving a small breather for lower-power laptops.
        loop.current = window.setTimeout(() => void tick(), 20);
      };
      void tick();
    } catch (reason) {
      await stop();
      setStarting(false);
      setError(reason instanceof Error ? reason.message : 'Não foi possível iniciar o controle por gestos.');
    }
  };

  useEffect(() => {
    const resize = () => { lastDimensions.current = { width: window.innerWidth, height: window.innerHeight }; };
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && enabled.current) {
        event.preventDefault();
        event.stopImmediatePropagation();
        void stop();
      }
    };
    window.addEventListener('resize', resize);
    window.addEventListener('keydown', key, true);
    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('keydown', key, true);
      void stop();
    };
  }, [stop]);

  return <>
    <video ref={video} className="hand-control-video" muted autoPlay playsInline aria-hidden="true" />
    {!active && !starting && <button className="reference-attachment" aria-label="Controlar computador com as mãos" title="Controle por gestos da mão" onClick={() => void start()}><Hand size={17} /></button>}
    {(active || starting) && <aside className="hand-control-status" role="status">
      <span className="hand-control-live" /><b>{starting ? 'PREPARANDO CONTROLE' : 'CRONOS · CONTROLE POR GESTOS'}</b>
      <p>{status}</p>
      {error && <p className="hand-control-error"><TriangleAlert size={13} />{error}</p>}
      <button onClick={() => void stop()} aria-label="Parar controle por gestos"><Square size={13} /> Parar</button>
    </aside>}
    {error && !active && !starting && <div className="hand-control-error-toast" role="alert"><TriangleAlert size={14} /><span>{error}</span><button onClick={() => setError('')} aria-label="Fechar aviso">×</button></div>}
    {active && <>
      <div className="hand-control-hologram" aria-label="Visualização holográfica das mãos rastreadas">
        <div className="hand-control-hologram-header"><span>RASTREAMENTO · 21 PONTOS</span><span className="hand-control-live" /></div>
        <svg viewBox="0 0 320 240" preserveAspectRatio="none" aria-hidden="true">
          <path className="hand-control-grid" d="M0 60H320 M0 120H320 M0 180H320 M80 0V240 M160 0V240 M240 0V240" />
          {hands.map((hand, index) => {
            const pts = hand.points.map((point) => ({ x: (1 - point.x) * 320, y: point.y * 240 }));
            return <g key={index} className="hand-control-skeleton">
              {connections.map(([a, b], edge) => <line key={edge} x1={pts[a].x} y1={pts[a].y} x2={pts[b].x} y2={pts[b].y} />)}
              {pts.map((point, node) => <circle key={node} cx={point.x} cy={point.y} r={node === 8 || node === 4 || node === 12 ? 4 : 2} />)}
              <text x={pts[0].x + 8} y={pts[0].y - 8}>{hand.side.toUpperCase()} · {hand.gesture}</text>
            </g>;
          })}
        </svg>
        <div className="hand-control-hologram-footer">{hands.length ? `${hands.length} ${hands.length === 1 ? 'MÃO' : 'MÃOS'} DETECTADA${hands.length === 1 ? '' : 'S'}` : 'AGUARDANDO MÃOS'}</div>
      </div>
      <svg className="hand-control-reticle-layer" viewBox={`0 0 ${lastDimensions.current.width} ${lastDimensions.current.height}`} preserveAspectRatio="none" aria-hidden="true">
        {cursor && <g className="hand-control-reticle"><circle cx={cursor.x} cy={cursor.y} r="15" /><circle cx={cursor.x} cy={cursor.y} r="3" /><path d={`M ${cursor.x - 22} ${cursor.y} H ${cursor.x - 11} M ${cursor.x + 11} ${cursor.y} H ${cursor.x + 22} M ${cursor.x} ${cursor.y - 22} V ${cursor.y - 11} M ${cursor.x} ${cursor.y + 11} V ${cursor.y + 22}`} /></g>}
      </svg>
    </>}
  </>;
}
