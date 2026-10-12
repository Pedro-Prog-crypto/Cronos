import React from 'react';
import { CronosCard } from '../types/cronos';
import { SecondaryCard } from './SecondaryCard';

interface SecondaryCardsTrayProps {
  cards: CronosCard[];
  activeCardId: string;
  onSelectCard: (card: CronosCard) => void;
  className?: string;
}

export const SecondaryCardsTray: React.FC<SecondaryCardsTrayProps> = ({
  cards,
  activeCardId,
  onSelectCard,
  className = '',
}) => {
  if (cards.length === 0) return null;

  return (
    <div
      className={`relative z-20 w-full max-w-5xl mx-auto px-4 transition-all duration-500 ${className}`}
    >
      <div className="flex items-center justify-center gap-2.5 sm:gap-3 flex-wrap py-2">
        {cards.map((card) => {
          const isActive = card.id === activeCardId;
          return (
            <div
              key={card.id}
              className="transform transition-all duration-500 ease-out"
            >
              <SecondaryCard
                card={card}
                isActive={isActive}
                onClick={() => onSelectCard(card)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
