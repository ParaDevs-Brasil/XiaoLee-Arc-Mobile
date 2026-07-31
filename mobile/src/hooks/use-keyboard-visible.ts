import { useEffect, useState } from 'react';
import { Keyboard, Platform } from 'react-native';

/**
 * Se o teclado está na tela.
 *
 * Existe por causa de um vão duplo no rodapé do chat: o card reserva
 * `insets.bottom` de margem para a barra de gestos, e quando o teclado sobe ele
 * cobre essa barra. Aí a margem deixa de separar o card do sistema e passa a
 * sobrar entre o composer e as teclas — no iOS o `KeyboardAvoidingView` já
 * empurrou a altura do teclado, então a margem vira folga pura.
 *
 * O iOS expõe os eventos `will*`, que disparam **junto** com a animação do
 * teclado; o Android só tem os `did*`, que chegam no fim dela (ver
 * `Keyboard.d.ts:82`). Usar o `will` onde existe é o que faz a margem sumir no
 * mesmo quadro em que o teclado sobe, em vez de dar um solavanco depois.
 */
export function useKeyboardVisible(): boolean {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // O setState mora no callback do listener, nunca no corpo do efeito — o
    // React Compiler (ligado em `app.json`) trata o segundo como render em
    // cascata (mesma regra citada em `use-backend-data.ts`).
    const show = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      () => setVisible(true),
    );
    const hide = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide',
      () => setVisible(false),
    );

    return () => {
      show.remove();
      hide.remove();
    };
  }, []);

  return visible;
}
