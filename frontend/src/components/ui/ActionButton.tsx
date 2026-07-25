import React from 'react';
import { ActionButtonProps } from '../../interfaces/campaignComponents'

const ActionButton: React.FC<ActionButtonProps> = ({ 
  onClick, 
  disabled, 
  loading, 
  loadingText, 
  children, 
  variant, 
  isLocked = false 
}) => {
  const variants = {
    primary: 'from-pink-400 to-purple-500 hover:from-pink-500 hover:to-purple-600',
    secondary: 'from-blue-400 to-teal-500 hover:from-blue-500 hover:to-teal-600',
    success: 'from-green-400 to-emerald-500 hover:from-green-500 hover:to-emerald-600'
  };

  if (isLocked) {
    return (
      <button
        onClick={onClick}
        className="w-full py-3 rounded-xl font-semibold transition-all duration-200 bg-gray-200 text-gray-500 border-2 border-dashed border-gray-300 hover:bg-gray-300 hover:border-gray-400"
      >
        🔒 {children}
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`w-full py-3 rounded-xl font-semibold transition-all duration-200 transform hover:scale-105 ${
        disabled || loading
          ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
          : `bg-gradient-to-r ${variants[variant]} text-white`
      }`}
    >
      {loading ? loadingText : children}
    </button>
  );
};

export default ActionButton;
