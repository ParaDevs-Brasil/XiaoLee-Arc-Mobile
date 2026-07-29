/**
 * Design tokens do XiaoLee — porta de `docs/DESIGN_SYSTEM.md` (revisão v4).
 *
 * Os valores foram conferidos contra o arquivo Figma "Xiaolee-Mobile"
 * (file key mxLRwIEczW8zCwn3Stx6ZP) e batem exatamente com o documento.
 * O equivalente web vive como CSS custom properties em
 * `frontend/src/app/globals.css` — mesmos hex, outro mecanismo.
 *
 * Regra de ouro do sistema: **acento só em botão primário, avatar e
 * destaques — o resto neutro.** Nos componentes, referencie sempre os tokens
 * daqui, nunca hex solto.
 */

import '@/global.css';

import { Platform } from 'react-native';

/** Paleta neutra quente com acento único de marca. */
const palette = {
  // Base
  bg: '#f6f4f1',
  card: '#ffffff',
  border: '#ece9e4',
  ink: '#1a1917',
  ink2: '#6b6862',
  ink3: '#9a968f',

  // Acento de marca — branco sobre accent = 4.8:1 (AA)
  accent: '#d81b78',
  accentHover: '#c0166a',
  accentSoft: '#fdf0f6',

  // Semânticas
  success: '#1f8a5b',
  successSoft: '#ecfdf5',
  successBorder: '#d0fae5',
  danger: '#c23a3a',
  dangerSoft: '#fef2f2',
} as const;

/**
 * As cinco primeiras chaves são as que `themed-text`/`themed-view` consomem
 * via `useTheme()`; o resto é o vocabulário completo do design system.
 */
const scheme = {
  text: palette.ink,
  background: palette.bg,
  backgroundElement: palette.card,
  backgroundSelected: palette.accentSoft,
  textSecondary: palette.ink2,
  ...palette,
} as const;

/**
 * O modo escuro está **suspenso** no design system até a paleta ganhar uma
 * variante escura — no web, `theme-context.tsx` força `light` e o toggle foi
 * removido da Navbar. `dark` aponta para os mesmos valores em vez de inventar
 * uma paleta escura que divergiria do produto.
 */
export const Colors = {
  light: scheme,
  dark: scheme,
} as const;

export type ThemeColor = keyof typeof scheme;

/**
 * Quicksand é a família do produto — o doc citava Inter, que nunca foi
 * implementada. Os nomes seguem os do pacote `@expo-google-fonts/quicksand`;
 * até `useFonts` resolver, o RN cai na fonte de sistema.
 */
export const Fonts = {
  sans: 'Quicksand_400Regular',
  medium: 'Quicksand_500Medium',
  semibold: 'Quicksand_600SemiBold',
  bold: 'Quicksand_700Bold',
  /**
   * Candice — fonte da marca, usada **só no logo**, igual à navbar web
   * (`--font-candice`). O arquivo é o `candice-web.ttf`, subset latino
   * re-serializado: o TTF original tem tabelas glyf/hmtx malformadas que os
   * sanitizadores de fonte rejeitam.
   */
  brand: 'Candice',
  mono: Platform.select({ ios: 'ui-monospace', default: 'monospace' }) as string,
} as const;

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

/** Raios medidos nos frames do Figma; `pill` para chips e botões redondos. */
export const Radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  pill: 999,
} as const;

/** Sombra sutil dos cards — equivalente ao `shadow-sm` do web. */
export const CardShadow = Platform.select({
  ios: {
    shadowColor: palette.ink,
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  android: { elevation: 1 },
  default: {},
});

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;
