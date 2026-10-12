import {Viewer} from 'cesium';
export function createApplicationViewer(options:{container:HTMLElement;creditContainer:HTMLElement}):Viewer;
export function installTrackpadPinchZoom(viewer:Viewer):()=>void;
