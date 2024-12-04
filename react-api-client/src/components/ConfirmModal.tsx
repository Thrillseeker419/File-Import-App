import React from 'react';

interface ConfirmModalProps {
  visible: boolean;
  text: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({ visible, text, onConfirm, onCancel }) => {
  if (!visible) return null;

  return (
    <div className={`confirm-modal-overlay ${visible ? 'visible' : ''}`}>
      <div className="confirm-modal">
        <p>{text}</p>
        <div className="modal-actions">
          <button onClick={onConfirm}>Confirm</button>
          <button onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;
