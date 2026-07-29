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
    <ThemeProvider value={DefaultTheme}>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: Colors.light.card },
          headerTitleStyle: { fontFamily: 'Quicksand_700Bold', color: Colors.light.ink },
          contentStyle: { backgroundColor: Colors.light.bg },
        }}
      >
        {/* O chat traz o próprio HeaderBar (o wordmark do Figma), então a
            barra nativa sairia duplicada. */}
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="diagnostics" options={{ title: 'Diagnóstico' }} />
      </Stack>
    </ThemeProvider>
  );
}
