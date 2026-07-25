import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  text?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  className = '',
  text
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl'
  };

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div 
        className={`${sizeClasses[size]} border-4 border-[var(--border)] border-t-[var(--accent)] rounded-full animate-spin`}
      />
      {text && (
        <p className={`mt-2 text-gray-600 ${textSizeClasses[size]} font-medium`}>
          {text}
        </p>
      )}
    </div>
  );
};

export const LoadingDots: React.FC<{ className?: string; text?: string }> = ({ 
  className = '', 
  text 
}) => {
  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
        <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
        <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
      </div>
      {text && (
        <p className="mt-2 text-gray-600 text-sm font-medium">
          {text}
        </p>
      )}
    </div>
  );
};

export const LoadingPulse: React.FC<{ className?: string; text?: string }> = ({ 
  className = '', 
  text 
}) => {
  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className="w-12 h-12 bg-[var(--accent-soft)] rounded-full animate-pulse"></div>
      {text && (
        <p className="mt-2 text-gray-600 text-base font-medium">
          {text}
        </p>
      )}
    </div>
  );
};

export default LoadingSpinner;
