import { Circle, Line, Path, Polyline, Svg } from 'react-native-svg';

/**
 * Ícones SVG inline — porta direta de `frontend/src/components/icons.tsx`.
 *
 * Os `d`/`points` são os mesmos do web para as duas plataformas desenharem o
 * mesmo traço. O design system proíbe emoji em UI e fixa o padrão em
 * `viewBox="0 0 24 24"`, stroke-based, `strokeWidth={1.8}` (seção 4).
 *
 * Só os ícones em uso estão aqui; o web tem ~50. Porte sob demanda em vez de
 * arrastar a biblioteca toda.
 */

export interface IconProps {
  /** Lado do quadrado, em px. */
  size?: number;
  /** Espessura do traço — 1.8 é o padrão do design system. */
  sw?: number;
  /** Cor do traço. Use tokens de `constants/theme`, nunca hex solto. */
  color?: string;
}

const base = ({ size = 24, sw = 1.8, color = 'currentColor' }: IconProps) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: color,
  strokeWidth: sw,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
});

export const IconBell = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
    <Path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </Svg>
);

/** Hambúrguer limpo — o `material-symbols:menu-rounded` do Figma. */
export const IconMenu = (p: IconProps) => (
  <Svg {...base(p)}>
    <Line x1="3" y1="6" x2="21" y2="6" />
    <Line x1="3" y1="12" x2="21" y2="12" />
    <Line x1="3" y1="18" x2="21" y2="18" />
  </Svg>
);

/** Lista com marcadores — não confundir com `IconMenu`. */
export const IconList = (p: IconProps) => (
  <Svg {...base(p)}>
    <Line x1="8" y1="6" x2="21" y2="6" />
    <Line x1="8" y1="12" x2="21" y2="12" />
    <Line x1="8" y1="18" x2="21" y2="18" />
    <Line x1="3" y1="6" x2="3.01" y2="6" />
    <Line x1="3" y1="12" x2="3.01" y2="12" />
    <Line x1="3" y1="18" x2="3.01" y2="18" />
  </Svg>
);

export const IconUser = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <Circle cx="12" cy="7" r="4" />
  </Svg>
);

export const IconGift = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M20 12v9H4v-9" />
    <Path d="M2 7h20v5H2z" />
    <Path d="M12 22V7" />
    <Path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z" />
    <Path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />
  </Svg>
);

export const IconActivity = (p: IconProps) => (
  <Svg {...base(p)}>
    <Polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </Svg>
);

export const IconSwap = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M7 10l-3 3 3 3" />
    <Path d="M4 13h13a3 3 0 0 0 3-3V7" />
    <Path d="M17 14l3-3-3-3" />
    <Path d="M20 11H7a3 3 0 0 0-3 3v3" />
  </Svg>
);

export const IconWallet = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M3 7a2 2 0 0 1 2-2h13v4" />
    <Path d="M3 7v10a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2z" />
    <Circle cx="16.5" cy="14" r="1.2" fill={p.color ?? 'currentColor'} stroke="none" />
  </Svg>
);

export const IconChat = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8A8.38 8.38 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z" />
  </Svg>
);

export const IconSend = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M22 2 11 13" />
    <Path d="M22 2 15 22l-4-9-9-4 20-7z" />
  </Svg>
);

export const IconCheck = (p: IconProps) => (
  <Svg {...base(p)}>
    <Path d="M20 6 9 17l-5-5" />
  </Svg>
);
