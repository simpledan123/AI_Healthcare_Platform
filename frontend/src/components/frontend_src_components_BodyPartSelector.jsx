// frontend/src/components/BodyPartSelector.jsx

import React from 'react';
import './BodyPartSelector.css';

const BodyPartSelector = ({ selectedPart, onSelect }) => {
  const bodyParts = [
    { id: 'neck', name: '목', icon: '🦴', color: '#FF6B6B' },
    { id: 'shoulder', name: '어깨', icon: '💪', color: '#4ECDC4' },
    { id: 'wrist', name: '손목', icon: '✋', color: '#45B7D1' },
    { id: 'waist', name: '허리', icon: '🔄', color: '#FFA07A' },
    { id: 'knee', name: '무릎', icon: '🦵', color: '#98D8C8' },
    { id: 'ankle', name: '발목', icon: '👣', color: '#C7CEEA' }
  ];

  return (
    <div className="body-part-selector">
      <h3 className="selector-title">어디가 불편하신가요?</h3>
      <div className="body-parts-grid">
        {bodyParts.map((part) => (
          <button
            key={part.id}
            className={`body-part-button ${selectedPart === part.name ? 'selected' : ''}`}
            onClick={() => onSelect(part.name)}
            style={{
              '--part-color': part.color,
              borderColor: selectedPart === part.name ? part.color : '#e0e0e0',
              backgroundColor: selectedPart === part.name ? `${part.color}15` : 'white'
            }}
          >
            <div className="part-icon">{part.icon}</div>
            <div className="part-name">{part.name}</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default BodyPartSelector;
