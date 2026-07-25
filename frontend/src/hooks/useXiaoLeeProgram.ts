/**
 * useXiaoLeeProgram — Hook para interagir com o programa Anchor on-chain XiaoLee Core
 *
 * IDL gerado em 2026-04-24 via `anchor build`.
 * Program ID: Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM (Devnet)
 *
 * Instruções disponíveis:
 *   - initialize_user(twitter_id: string) — cria PDA de usuário
 *   - initialize_global()                — admin only: inicializa GlobalConfig
 *   - record_swap(volume: u64)           — admin only: registra swap on-chain
 *
 * Este hook é somente-leitura (fetch de UserState via PDA).
 * Escritas on-chain são feitas pelo backend (record_swap com autoridade admin).
 */
import { useState, useEffect, useCallback } from 'react';
import { Connection, PublicKey, clusterApiUrl } from '@solana/web3.js';
import * as anchor from '@coral-xyz/anchor';
import type { Idl } from '@coral-xyz/anchor';

// ─── Constantes ────────────────────────────────────────────────────────────────

export const XIAOLEE_PROGRAM_ID = new PublicKey(
  'Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM'
);

// Cluster alinhado com o Devnet onde o programa está deployado.
// IMPORTANTE: manter em sincronia com o ambiente real de deploy.
export const XIAOLEE_CLUSTER: 'devnet' | 'mainnet-beta' = 'devnet';

// ─── IDL real gerado por `anchor build` ────────────────────────────────────────

const XIAOLEE_IDL: Idl = {
  address: 'Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM',
  metadata: {
    name: 'xiaolee_core',
    version: '0.1.0',
    spec: '0.1.0',
    description: 'Created with Anchor',
  },
  instructions: [
    {
      name: 'initialize_global',
      discriminator: [47, 225, 15, 112, 86, 51, 190, 231],
      accounts: [
        {
          name: 'global_config',
          writable: true,
          pda: {
            seeds: [
              { kind: 'const', value: [103, 108, 111, 98, 97, 108, 95, 99, 111, 110, 102, 105, 103] },
            ],
          },
        },
        { name: 'admin', writable: true, signer: true },
        { name: 'system_program', address: '11111111111111111111111111111111' },
      ],
      args: [],
    },
    {
      name: 'initialize_user',
      discriminator: [111, 17, 185, 250, 60, 122, 38, 254],
      accounts: [
        {
          name: 'user_state',
          writable: true,
          pda: {
            seeds: [
              { kind: 'const', value: [117, 115, 101, 114] }, // "user"
              { kind: 'arg', path: 'twitter_id' },
            ],
          },
        },
        { name: 'user', writable: true, signer: true },
        { name: 'system_program', address: '11111111111111111111111111111111' },
      ],
      args: [{ name: 'twitter_id', type: 'string' }],
    },
    {
      name: 'record_swap',
      discriminator: [164, 158, 148, 54, 167, 137, 171, 59],
      accounts: [
        {
          name: 'global_config',
          pda: {
            seeds: [
              { kind: 'const', value: [103, 108, 111, 98, 97, 108, 95, 99, 111, 110, 102, 105, 103] },
            ],
          },
        },
        {
          name: 'user_state',
          writable: true,
          pda: {
            seeds: [
              { kind: 'const', value: [117, 115, 101, 114] },
              { kind: 'account', path: 'user_state.twitter_id', account: 'UserState' },
            ],
          },
        },
        { name: 'admin', writable: true, signer: true, relations: ['global_config'] },
      ],
      args: [{ name: 'volume', type: 'u64' }],
    },
  ],
  accounts: [
    { name: 'GlobalConfig', discriminator: [149, 8, 156, 202, 160, 252, 176, 217] },
    { name: 'UserState', discriminator: [72, 177, 85, 249, 76, 167, 186, 126] },
  ],
  errors: [
    { code: 6000, name: 'MathOverflow', msg: 'Math operation overflow' },
    { code: 6001, name: 'StringTooLong', msg: 'String length exceeds maximum allowed limit of 50' },
    { code: 6002, name: 'Unauthorized', msg: 'Unauthorized: You are not the protocol admin' },
  ],
  types: [
    {
      name: 'GlobalConfig',
      type: {
        kind: 'struct',
        fields: [
          { name: 'admin', type: 'pubkey' },
          { name: 'bump', type: 'u8' },
        ],
      },
    },
    {
      name: 'UserState',
      type: {
        kind: 'struct',
        fields: [
          { name: 'twitter_id', type: 'string' },
          { name: 'swap_count', type: 'u64' },
          { name: 'total_volume', type: 'u64' },
          { name: 'bump', type: 'u8' },
        ],
      },
    },
  ],
} as unknown as Idl;

// ─── Tipos ─────────────────────────────────────────────────────────────────────

export interface XiaoLeeUserState {
  twitterId: string;
  swapCount: number;
  totalVolume: number; // em lamports (9 casas decimais para SOL, 6 para USDC)
  bump: number;
}

// ─── Utilitários ───────────────────────────────────────────────────────────────

/**
 * Deriva o endereço PDA de um usuário dado seu twitter_id.
 * Seed: ["user", twitter_id_bytes]
 */
export function deriveUserStatePda(twitterId: string): PublicKey {
  const [pda] = PublicKey.findProgramAddressSync(
    [Buffer.from('user'), Buffer.from(twitterId)],
    XIAOLEE_PROGRAM_ID
  );
  return pda;
}

/**
 * Deriva o endereço PDA de GlobalConfig.
 * Seed: ["global_config"]
 */
export function deriveGlobalConfigPda(): PublicKey {
  const [pda] = PublicKey.findProgramAddressSync(
    [Buffer.from('global_config')],
    XIAOLEE_PROGRAM_ID
  );
  return pda;
}

// ─── Hook principal ────────────────────────────────────────────────────────────

export type XiaoLeeProgramErrorCode = 'not_found' | 'connection_error' | null;

// Devnet session tokens (devnet_wallet_* / devnet_guest_*) are frontend-only
// identifiers and never correspond to on-chain UserState accounts. They also
// frequently exceed the 32-byte PDA seed limit, causing a hard crash.
function isRealTwitterId(id: string | null): boolean {
  if (!id) return false;
  if (id.startsWith('devnet_')) return false;
  if (Buffer.from(id).length > 32) return false;
  return true;
}

export function useXiaoLeeProgram(twitterId: string | null) {
  const [userState, setUserState] = useState<XiaoLeeUserState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<XiaoLeeProgramErrorCode>(null);

  const fetchUserState = useCallback(async () => {
    if (!isRealTwitterId(twitterId)) {
      setUserState(null);
      setErrorCode(null);
      return;
    }

    setLoading(true);
    setError(null);
    setErrorCode(null);

    try {
      const connection = new Connection(clusterApiUrl(XIAOLEE_CLUSTER), 'confirmed');

      // Wallet read-only — não precisa de chave privada para apenas ler
      const readOnlyWallet = {
        publicKey: PublicKey.default,
        signTransaction: async <T>(tx: T) => tx,
        signAllTransactions: async <T>(txs: T[]) => txs,
      } as unknown as anchor.Wallet;

      const provider = new anchor.AnchorProvider(connection, readOnlyWallet, {
        preflightCommitment: 'confirmed',
      });

      const program = new anchor.Program(XIAOLEE_IDL, provider);

      const pda = deriveUserStatePda(twitterId as string);

      // Fetch da conta UserState via PDA derivado
      // O IDL real garante que o decode está correto com os campos do contrato
      const account = await (program.account as unknown as {
        userState: {
          fetch: (addr: PublicKey) => Promise<{
            twitterId: string;
            swapCount: anchor.BN;
            totalVolume: anchor.BN;
            bump: number;
          }>;
        };
      }).userState.fetch(pda);

      setUserState({
        twitterId: account.twitterId,
        swapCount: account.swapCount.toNumber(),
        totalVolume: account.totalVolume.toNumber(),
        bump: account.bump,
      });
    } catch (err: unknown) {
      const isNotFound =
        err instanceof Error && err.message.toLowerCase().includes('account does not exist');

      if (isNotFound) {
        setErrorCode('not_found');
        setError('not_found');
      } else {
        console.warn('[useXiaoLeeProgram] Erro ao buscar UserState:', err);
        setErrorCode('connection_error');
        setError('connection_error');
      }
      setUserState(null);
    } finally {
      setLoading(false);
    }
  }, [twitterId]);

  useEffect(() => {
    fetchUserState();
  }, [fetchUserState]);

  return {
    userState,
    loading,
    error,
    errorCode,
    refetch: fetchUserState,
    /** PDA derivado para uso externo (ex: exibir explorer link) */
    userStatePda: isRealTwitterId(twitterId) ? deriveUserStatePda(twitterId as string) : null,
  };
}
