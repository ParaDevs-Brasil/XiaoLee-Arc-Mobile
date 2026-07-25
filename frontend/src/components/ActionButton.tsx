import React from 'react';
import { ActionButtonProps } from '@/interfaces/campaignComponents';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

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
    primary:   'from-pink-400 via-fuchsia-500 to-purple-500 hover:from-pink-500 hover:to-purple-600',
    secondary: 'from-violet-400 to-indigo-500 hover:from-violet-500 hover:to-indigo-600',
    success:   'from-emerald-400 to-teal-500 hover:from-emerald-500 hover:to-teal-600',
  };

  if (isLocked) {
    return (
      <button
        disabled
        className="w-full py-2.5 rounded-xl text-sm font-semibold bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed"
      >
        {children}
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
        disabled || loading
          ? 'bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed'
          : `bg-gradient-to-r ${variants[variant]} text-white shadow-sm hover:shadow-md hover:scale-[1.02] active:scale-[0.98]`
      }`}
    >
      {loading ? (
        <div className="flex items-center justify-center gap-2">
          <LoadingSpinner size="sm" className="text-white" />
          <span>{loadingText}</span>
        </div>
      ) : (
        children
      )}
    </button>
  );
};

export default ActionButton;
