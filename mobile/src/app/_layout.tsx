import {
  Quicksand_400Regular,
  Quicksand_500Medium,
  Quicksand_600SemiBold,
  Quicksand_700Bold,
  useFonts,
} from '@expo-google-fonts/quicksand';
import { DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Colors } from '@/constants/theme';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  // Quicksand é a fonte do produto (ver constants/theme.ts). Sem esperar por
  // ela, o app pisca na fonte de sistema antes de trocar.
  const [fontsLoaded, fontError] = useFonts({
    Quicksand_400Regular,
    Quicksand_500Medium,
    Quicksand_600SemiBold,
    Quicksand_700Bold,
    // Candice: fonte da marca, só o logo usa (ver Fonts.brand).
    Candice: require('../../assets/fonts/candice-web.ttf'),
  });

  useEffect(() => {
    // Falha de fonte não deve prender o usuário no splash — segue na de sistema.
    if (!fontsLoaded && !fontError) return;
    SplashScreen.hideAsync().catch(() => {
      // splash já escondido — não há o que tratar
    });
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) return null;

  return (
    // Tema claro fixo: o design system suspendeu o modo escuro até a paleta
    // ganhar variante escura (o web também força light).
    // SafeAreaProvider é obrigatório para `useSafeAreaInsets` devolver algo
    // diferente de zero — sem ele o header fica sob a status bar.
    <SafeAreaProvider>
      <ThemeProvider value={DefaultTheme}>
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: Colors.light.card },
            headerTitleStyle: { fontFamily: 'Quicksand_700Bold', color: Colors.light.ink },
            contentStyle: { backgroundColor: Colors.light.bg },
          }}
        >
          {/* Estas telas trazem o próprio HeaderBar (o wordmark do Figma) via
              `ScreenShell`, então a barra nativa sairia duplicada. A volta
              fica com o gesto do sistema e com o wordmark, que leva ao chat. */}
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="traction" options={{ headerShown: false }} />
          <Stack.Screen name="notifications" options={{ headerShown: false }} />
          <Stack.Screen name="campaigns/index" options={{ headerShown: false }} />
          {/* O formulário é a exceção: entra como modal e mantém a barra
              nativa. Num formulário longo o usuário precisa de uma saída
              sempre visível, e o wordmark do ScreenShell não é uma. */}
          <Stack.Screen
            name="campaigns/new"
            options={{ presentation: 'modal', title: 'New Campaign' }}
          />
          <Stack.Screen name="diagnostics" options={{ title: 'Diagnóstico' }} />
        </Stack>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
