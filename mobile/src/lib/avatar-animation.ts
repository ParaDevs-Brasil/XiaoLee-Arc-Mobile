/**
 * Máquina de estados das animações da Xiaolee — porta de
 * `frontend/src/components/Video.tsx`.
 *
 * A lógica é a mesma do web de propósito: a personagem alterna entre idles em
 * loop e expressões que tocam uma vez, e uma expressão em andamento **trava**
 * as trocas até terminar. Divergir aqui faria a personagem se comportar como
 * dois produtos diferentes.
 *
 * Módulo puro: nada de React, de `react-native` ou de `require` de asset — o
 * mapa de arquivos vive em `AnimatedAvatar`, que é quem renderiza. É isso que
 * permite rodar `avatar-animation.test.ts` em Node, sem bundler.
 *
 * Diferenças conscientes em relação ao web:
 *  - `EXPRESSION_CHANCE` menor: o web foi calibrado em desktop na tomada;
 *    no celular cada troca custa decodificação e bateria.
 *  - `stop()` existe para o app pausar quando vai para background.
 */

/** Chave da animação — o nome do arquivo sem extensão, igual ao web. */
export type AnimationKey =
  | 'xiaolee_standby'
  | 'xiaolee_standby2'
  | 'xiaolee_standby3'
  | 'xiaolee_cheer'
  | 'xiaolee_kawaii'
  | 'xiaolee_giggle'
  | 'xiaolee_love'
  | 'xiaolee_surprise'
  | 'xiaolee_uncomfortable'
  | 'xiaolee_hello'
  | 'xiaolee_salute'
  | 'xiaolee_ouch'
  | 'xiaolee_thinklow';

/**
 * Nomes de animação que o backend devolve no campo `animations` de
 * `POST /chat` — espelho de `ACTION_VIDEO_MAP` em `backend/config.py`.
 *
 * Vários nomes caem no mesmo clipe de propósito (Happy → kawaii,
 * Excited → cheer): o modelo escolhe pelo sentimento, não pelo arquivo.
 */
const BACKEND_ANIMATIONS: Record<string, AnimationKey> = {
  Cheer: 'xiaolee_cheer',
  Giggle: 'xiaolee_giggle',
  Kawaii: 'xiaolee_kawaii',
  Love: 'xiaolee_love',
  Hello: 'xiaolee_hello',
  Surprise: 'xiaolee_surprise',
  Uncomfortable: 'xiaolee_uncomfortable',
  Ouch: 'xiaolee_ouch',
  'Think Low': 'xiaolee_thinklow',
  Salute: 'xiaolee_salute',
  Happy: 'xiaolee_kawaii',
  Excited: 'xiaolee_cheer',
  Confused: 'xiaolee_thinklow',
  Thinking: 'xiaolee_thinklow',
  Standby: 'xiaolee_standby',
  Standby2: 'xiaolee_standby2',
  Standby3: 'xiaolee_standby3',
  wave: 'xiaolee_hello',
  celebration: 'xiaolee_cheer',
  success: 'xiaolee_cheer',
  error: 'xiaolee_ouch',
};

/**
 * Converte o nome vindo do backend em chave de animação.
 *
 * Devolve `null` para nome desconhecido em vez de cair num padrão: o backend
 * pode ganhar animações novas antes do app, e tocar o clipe errado é pior do
 * que continuar no idle.
 */
export function animationFromBackend(name: unknown): AnimationKey | null {
  if (typeof name !== 'string') return null;
  return BACKEND_ANIMATIONS[name] ?? null;
}

/** Idles fazem loop e podem ser interrompidos a qualquer momento. */
const IDLE: AnimationKey[] = ['xiaolee_standby', 'xiaolee_standby2', 'xiaolee_standby3'];

/** Expressões tocam uma vez e travam as trocas enquanto rodam. */
const EXPRESSIONS: AnimationKey[] = [
  'xiaolee_cheer',
  'xiaolee_kawaii',
  'xiaolee_giggle',
  'xiaolee_love',
  'xiaolee_surprise',
  'xiaolee_uncomfortable',
];

/** Chance de tocar expressão em vez de trocar de idle. Web usa 0.45. */
const EXPRESSION_CHANCE = 0.3;

/** Janela do sorteio do próximo idle, em ms. */
const IDLE_DELAY_MIN = 8_000;
const IDLE_DELAY_MAX = 15_000;

export interface AnimationState {
  key: AnimationKey;
  /** Idles fazem loop; expressões tocam uma vez. */
  loop: boolean;
}

type Listener = (state: AnimationState) => void;

function pick<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

export function isIdle(key: AnimationKey): boolean {
  return IDLE.includes(key);
}

/**
 * Controlador das animações. Instanciável (o web usa estático) para que testes
 * e telas diferentes não compartilhem timer sem querer.
 */
export class AvatarAnimation {
  private current: AnimationKey = 'xiaolee_standby';
  private listeners: Listener[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;
  /** Trava enquanto uma expressão toca — idles não travam. */
  private locked = false;

  get state(): AnimationState {
    return { key: this.current, loop: isIdle(this.current) };
  }

  subscribe(listener: Listener): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  /** Troca a animação. Ignorado se uma expressão estiver tocando. */
  play(key: AnimationKey): void {
    if (this.locked) return;

    this.clearTimer();
    this.current = key;
    const loop = isIdle(key);
    // Só expressão trava; idle segue interrompível.
    this.locked = !loop;

    for (const listener of this.listeners) listener({ key, loop });
    if (loop) this.scheduleNext();
  }

  /**
   * Chamado quando uma expressão termina — volta para um idle sorteado.
   *
   * No-op se nenhuma expressão estiver tocando: quem exibe assina o fim de
   * vídeo nos dois players do crossfade sem saber qual está à frente, então
   * chamadas espúrias são esperadas e não devem cortar um idle no meio.
   */
  expressionEnded(): void {
    if (!this.locked) return;
    this.locked = false;
    this.play(pick(IDLE));
  }

  /** Começa o ciclo. Idempotente. */
  start(): void {
    if (this.timer) return;
    this.play(pick(IDLE));
  }

  /** Para o ciclo sem mexer na animação corrente (app em background). */
  stop(): void {
    this.clearTimer();
    this.locked = false;
  }

  private clearTimer(): void {
    if (!this.timer) return;
    clearTimeout(this.timer);
    this.timer = null;
  }

  private scheduleNext(): void {
    const delay = IDLE_DELAY_MIN + Math.random() * (IDLE_DELAY_MAX - IDLE_DELAY_MIN);
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.locked) return;

      if (Math.random() < EXPRESSION_CHANCE) {
        this.play(pick(EXPRESSIONS));
        return;
      }
      // Evita repetir o idle atual, que pareceria travado.
      const others = IDLE.filter((k) => k !== this.current);
      this.play(pick(others.length > 0 ? others : IDLE));
    }, delay);
  }
}

/**
 * Instância compartilhada por quem exibe o avatar e por quem reage ao chat —
 * o web usa uma classe estática pelo mesmo motivo. A classe segue
 * instanciável para os testes não dividirem timer com o app.
 */
export const avatarAnimation = new AvatarAnimation();
