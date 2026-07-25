// Organized interfaces re-exports for Xiaolee project

// Chat interfaces
export * from './chat';

// User interfaces  
export * from './user';

// Campaign interfaces
export * from './campaign';

// Campaign component interfaces
export * from './campaignComponents';

// Component-specific interfaces (deprecated - use specific imports)
export type { HistoricoProps } from './chat';
export type { WalletProps, TransacoesProps } from './user';
