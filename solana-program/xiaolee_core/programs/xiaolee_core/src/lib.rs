use anchor_lang::prelude::*;

declare_id!("Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM");

// ─── Versão do protocolo ───────────────────────────────────────────────────────
// Incrementar a cada breaking change no schema de contas.
pub const PROTOCOL_VERSION: u8 = 1;

#[program]
pub mod xiaolee_core {
    use super::*;

    /// Inicializa o GlobalConfig do protocolo — executado UMA VEZ pelo admin.
    /// Após deploy em mainnet, execute: anchor run initialize_global
    pub fn initialize_global(ctx: Context<InitializeGlobal>) -> Result<()> {
        let global_config = &mut ctx.accounts.global_config;
        global_config.admin = ctx.accounts.admin.key();
        global_config.bump = ctx.bumps.global_config;
        global_config.paused = false;
        global_config.version = PROTOCOL_VERSION;
        global_config.total_swaps_recorded = 0;

        emit!(GlobalInitialized {
            admin: global_config.admin,
            version: global_config.version,
        });

        msg!(
            "GlobalConfig initialized | admin={} | version={}",
            global_config.admin,
            global_config.version
        );
        Ok(())
    }

    /// Inicializa a conta UserState de um usuário — pago pelo próprio usuário.
    pub fn initialize_user(ctx: Context<InitializeUser>, twitter_id: String) -> Result<()> {
        // Sanitização de input: twitter_id limitado a 50 chars
        require!(twitter_id.len() <= 50, ErrorCode::StringTooLong);

        // Protocolo não pode estar pausado para novos usuários
        require!(!ctx.accounts.global_config.paused, ErrorCode::ProtocolPaused);

        let user_state = &mut ctx.accounts.user_state;
        user_state.twitter_id = twitter_id;
        user_state.swap_count = 0;
        user_state.total_volume = 0;
        user_state.bump = ctx.bumps.user_state;

        msg!("User {} initialized successfully!", user_state.twitter_id);
        Ok(())
    }

    /// Registra um swap confirmado on-chain — chamado APENAS pelo admin.
    /// O constraint has_one = admin garante que apenas o admin assina.
    /// Best-effort: chamado pelo backend após confirmação via Helius webhook.
    pub fn record_swap(ctx: Context<RecordSwap>, volume: u64) -> Result<()> {
        // Protocolo deve estar ativo
        require!(!ctx.accounts.global_config.paused, ErrorCode::ProtocolPaused);

        let user_state = &mut ctx.accounts.user_state;
        let global_config = &mut ctx.accounts.global_config;

        // Aritmética segura: previne panic por overflow
        user_state.swap_count = user_state
            .swap_count
            .checked_add(1)
            .ok_or(ErrorCode::MathOverflow)?;

        user_state.total_volume = user_state
            .total_volume
            .checked_add(volume)
            .ok_or(ErrorCode::MathOverflow)?;

        global_config.total_swaps_recorded = global_config
            .total_swaps_recorded
            .checked_add(1)
            .ok_or(ErrorCode::MathOverflow)?;

        emit!(SwapRecorded {
            twitter_id: user_state.twitter_id.clone(),
            swap_count: user_state.swap_count,
            volume,
            total_volume: user_state.total_volume,
        });

        msg!(
            "Swap recorded | user={} | count={} | volume={} | total_vol={}",
            user_state.twitter_id,
            user_state.swap_count,
            volume,
            user_state.total_volume
        );
        Ok(())
    }

    // ─── Emergency Controls ────────────────────────────────────────────────────

    /// Pausa o protocolo em emergência — APENAS o admin pode chamar.
    /// Quando pausado: record_swap e initialize_user rejeitam todas as chamadas.
    /// Padrão CEI: checks primeiro, effects depois, sem interactions externas.
    pub fn pause_protocol(ctx: Context<AdminAction>) -> Result<()> {
        let global_config = &mut ctx.accounts.global_config;

        require!(!global_config.paused, ErrorCode::AlreadyPaused);

        global_config.paused = true;

        emit!(ProtocolPaused {
            admin: ctx.accounts.admin.key(),
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!(
            "⚠️  PROTOCOLO PAUSADO por {} — nenhuma operação aceita",
            ctx.accounts.admin.key()
        );
        Ok(())
    }

    /// Retoma o protocolo após emergência — APENAS o admin pode chamar.
    pub fn unpause_protocol(ctx: Context<AdminAction>) -> Result<()> {
        let global_config = &mut ctx.accounts.global_config;

        require!(global_config.paused, ErrorCode::NotPaused);

        global_config.paused = false;

        emit!(ProtocolUnpaused {
            admin: ctx.accounts.admin.key(),
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!(
            "✅ Protocolo retomado por {}",
            ctx.accounts.admin.key()
        );
        Ok(())
    }

    /// Transfere a autoridade de admin para um novo endereço.
    /// Requer aprovação do admin atual — para uso com multisig Gnosis Safe.
    pub fn transfer_admin(ctx: Context<TransferAdmin>, new_admin: Pubkey) -> Result<()> {
        require!(new_admin != Pubkey::default(), ErrorCode::InvalidAdminAddress);

        let global_config = &mut ctx.accounts.global_config;
        let old_admin = global_config.admin;
        global_config.admin = new_admin;

        emit!(AdminTransferred {
            old_admin,
            new_admin,
            timestamp: Clock::get()?.unix_timestamp,
        });

        msg!("Admin transferido de {} para {}", old_admin, new_admin);
        Ok(())
    }
}

// ─── Contextos de Conta ────────────────────────────────────────────────────────

#[derive(Accounts)]
pub struct InitializeGlobal<'info> {
    #[account(
        init,
        payer = admin,
        space = 8 + GlobalConfig::INIT_SPACE,
        seeds = [b"global_config"],
        bump
    )]
    pub global_config: Account<'info, GlobalConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(twitter_id: String)]
pub struct InitializeUser<'info> {
    #[account(
        seeds = [b"global_config"],
        bump = global_config.bump,
    )]
    pub global_config: Account<'info, GlobalConfig>,

    #[account(
        init,
        payer = user,
        space = 8 + UserState::INIT_SPACE,
        seeds = [b"user", twitter_id.as_bytes()],
        bump
    )]
    pub user_state: Account<'info, UserState>,

    #[account(mut)]
    pub user: Signer<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct RecordSwap<'info> {
    #[account(
        mut,
        seeds = [b"global_config"],
        bump = global_config.bump,
        has_one = admin @ ErrorCode::Unauthorized
    )]
    pub global_config: Account<'info, GlobalConfig>,

    #[account(
        mut,
        seeds = [b"user", user_state.twitter_id.as_bytes()],
        bump = user_state.bump
    )]
    pub user_state: Account<'info, UserState>,

    #[account(mut)]
    pub admin: Signer<'info>,
}

#[derive(Accounts)]
pub struct AdminAction<'info> {
    #[account(
        mut,
        seeds = [b"global_config"],
        bump = global_config.bump,
        has_one = admin @ ErrorCode::Unauthorized
    )]
    pub global_config: Account<'info, GlobalConfig>,

    pub admin: Signer<'info>,
}

#[derive(Accounts)]
pub struct TransferAdmin<'info> {
    #[account(
        mut,
        seeds = [b"global_config"],
        bump = global_config.bump,
        has_one = admin @ ErrorCode::Unauthorized
    )]
    pub global_config: Account<'info, GlobalConfig>,

    pub admin: Signer<'info>,
}

// ─── Schemas de Conta ─────────────────────────────────────────────────────────

#[account]
#[derive(InitSpace)]
pub struct GlobalConfig {
    /// Endereço do admin atual (pode ser multisig Gnosis Safe em produção)
    pub admin: Pubkey,
    /// Bump seed da PDA
    pub bump: u8,
    /// Estado de pausa emergencial — quando true, bloqueia todas as operações
    pub paused: bool,
    /// Versão do protocolo para gestão de upgrades
    pub version: u8,
    /// Total de swaps gravados no protocolo (rastreabilidade on-chain)
    pub total_swaps_recorded: u64,
}

#[account]
#[derive(InitSpace)]
pub struct UserState {
    #[max_len(50)]
    pub twitter_id: String,
    pub swap_count: u64,
    pub total_volume: u64,
    pub bump: u8,
}

// ─── Eventos (on-chain indexing) ───────────────────────────────────────────────

#[event]
pub struct GlobalInitialized {
    pub admin: Pubkey,
    pub version: u8,
}

#[event]
pub struct SwapRecorded {
    pub twitter_id: String,
    pub swap_count: u64,
    pub volume: u64,
    pub total_volume: u64,
}

#[event]
pub struct ProtocolPaused {
    pub admin: Pubkey,
    pub timestamp: i64,
}

#[event]
pub struct ProtocolUnpaused {
    pub admin: Pubkey,
    pub timestamp: i64,
}

#[event]
pub struct AdminTransferred {
    pub old_admin: Pubkey,
    pub new_admin: Pubkey,
    pub timestamp: i64,
}

// ─── Códigos de Erro ──────────────────────────────────────────────────────────

#[error_code]
pub enum ErrorCode {
    #[msg("Math operation overflow")]
    MathOverflow,

    #[msg("String length exceeds maximum allowed limit of 50")]
    StringTooLong,

    #[msg("Unauthorized: You are not the protocol admin")]
    Unauthorized,

    #[msg("Protocol is paused — no operations accepted")]
    ProtocolPaused,

    #[msg("Protocol is already paused")]
    AlreadyPaused,

    #[msg("Protocol is not paused")]
    NotPaused,

    #[msg("Invalid admin address — cannot be default pubkey")]
    InvalidAdminAddress,
}
