import { useEffect, useState } from 'react';
import { Keyboard, Platform } from 'react-native';

/**
 * Estado do teclado do sistema.
 *
 * Existe porque desde o SDK 54 o edge-to-edge é obrigatório no Android e a
 * janela não encolhe mais quando o teclado sobe — o app desenha atrás dele.
 * Sem medir o teclado, o rodapé de qualquer tela com campo fica coberto.
 *
 * A `height` vem do `endCoordinates` do evento, medida a partir da base da
 * tela. É exata porque não depende de geometria de layout nenhuma: é o próprio
 * sistema dizendo quanto da tela o teclado ocupa — diferente da conta do
 * `KeyboardAvoidingView`, que mistura o `y` do layout (relativo ao pai) com o
 * `screenY` do teclado (absoluto) e só fecha quando a raiz React começa no topo
 * da tela.
 *
 * O `visible` responde a outra pergunta: com o teclado aberto ele cobre a barra
 * de gestos, então o `insets.bottom` deixa de proteger de alguma coisa e vira
 * folga entre o conteúdo e as teclas.
 */
export interface KeyboardState {
  visible: boolean;
  /** Altura do teclado em dp, a partir da base da tela. `0` com ele fechado. */
  height: number;
}

/**
 * O iOS expõe os eventos `will*`, que disparam **junto** com a animação do
 * teclado; o Android só tem os `did*`, que chegam no fim dela (ver
 * `Keyboard.d.ts:82`). Usar o `will` onde existe é o que faz o layout se
 * ajustar no mesmo quadro em que o teclado sobe, em vez de dar um solavanco
 * depois.
 */
const SHOW = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
const HIDE = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';

export function useKeyboard(): KeyboardState {
  // Um estado só, e não dois: `visible` e `height` mudam sempre juntos, e
  // separá-los daria um render intermediário anunciando "aberto, altura 0".
  const [state, setState] = useState<KeyboardState>({ visible: false, height: 0 });

  useEffect(() => {
    // O setState mora no callback do listener, nunca no corpo do efeito — o
    // React Compiler (ligado em `app.json`) trata o segundo como render em
    // cascata (mesma regra citada em `use-backend-data.ts`).
    const show = Keyboard.addListener(SHOW, (event) => {
      setState({ visible: true, height: event.endCoordinates?.height ?? 0 });
    });
    const hide = Keyboard.addListener(HIDE, () => {
      setState({ visible: false, height: 0 });
    });

    return () => {
      show.remove();
      hide.remove();
    };
  }, []);

  return state;
}
