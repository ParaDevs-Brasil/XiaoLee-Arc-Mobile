import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, type ViewStyle } from 'react-native';

const FADE_MS = 400;

interface FadeOutOverlayProps {
  /** Parent flips this to `true` to start the dissolve — stays mounted until it finishes. */
  fadeOut: boolean;
  /** Fired once opacity hits 0 — safe for the parent to actually unmount now. */
  onFadedOut: () => void;
  zIndex: number;
  children: React.ReactNode;
}

/**
 * Faz a camada se dissolver (opacity 1 → 0) em vez de sumir de uma vez —
 * usado para os cortes secos entre vídeo de intro → loading → chat. A
 * camada de baixo (a próxima) já está montada e visível o tempo todo; só
 * esta aqui anima, revelando-a por baixo aos poucos.
 */
export function FadeOutOverlay({ fadeOut, onFadedOut, zIndex, children }: FadeOutOverlayProps) {
  const opacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!fadeOut) return;
    Animated.timing(opacity, {
      toValue: 0,
      duration: FADE_MS,
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (finished) onFadedOut();
    });
  }, [fadeOut, onFadedOut, opacity]);

  const style: ViewStyle = { ...StyleSheet.absoluteFill, zIndex };

  return (
    <Animated.View pointerEvents={fadeOut ? 'none' : 'auto'} style={[style, { opacity }]}>
      {children}
    </Animated.View>
  );
}
