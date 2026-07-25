"use client";

import React from "react";

interface ModalProps {
  isOpen: boolean;
  animateIn: boolean;
  onBackdropClick: () => void;
  /** Classes do cartão do modal — cada uso mantém seu próprio visual (branco/e3, gradiente/accent, etc). */
  boxClassName: string;
  children: React.ReactNode;
}

/**
 * Overlay + cartão animado compartilhado por todos os modais do app —
 * cada chamador decide seu próprio visual via `boxClassName` e continua
 * dono do seu `useModal()` (isOpen/animateIn/closeModal ficam no chamador,
 * já que efeitos internos costumam depender de `isOpen`).
 */
export const Modal: React.FC<ModalProps> = ({ isOpen, animateIn, onBackdropClick, boxClassName, children }) => {
  if (!isOpen) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300 ${
        animateIn ? "bg-black/30 backdrop-blur-sm" : "bg-black/0"
      }`}
      onClick={onBackdropClick}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`${boxClassName} transition-all duration-300 transform ${
          animateIn ? "scale-100 opacity-100 translate-y-0" : "scale-95 opacity-0 translate-y-4"
        }`}
      >
        {children}
      </div>
    </div>
  );
};

export default Modal;
