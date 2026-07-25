import { useCallback, useEffect, useState } from 'react';

export const useModal = (shouldOpen: boolean = false, onClose?: () => void) => {
  const [isOpen, setIsOpen] = useState(false);
  const [animateIn, setAnimateIn] = useState(false);

  // Handle shouldOpen prop
  useEffect(() => {
    if (shouldOpen && !isOpen) {
      setIsOpen(true);
      setTimeout(() => setAnimateIn(true), 10);
    }
  }, [shouldOpen, isOpen]);

  const closeModal = useCallback(() => {
    setAnimateIn(false);
    setTimeout(() => {
      setIsOpen(false);
      if (onClose) onClose();
    }, 300);
  }, [onClose]);

  // Handle ESC key to close modal
  useEffect(() => {
    // Só adiciona event listeners no lado do cliente
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        closeModal();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen, closeModal]);

  return {
    isOpen,
    animateIn,
    closeModal,
  };
};
