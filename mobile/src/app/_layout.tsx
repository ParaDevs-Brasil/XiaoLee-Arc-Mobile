import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { useColorScheme } from 'react-native';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const colorScheme = useColorScheme();

  useEffect(() => {
    // Nada assíncrono para carregar ainda (fontes, sessão restaurada, etc.).
    // Quando houver, mova o hide para depois desse carregamento.
    SplashScreen.hideAsync().catch(() => {
      // splash já escondido — não há o que tratar
    });
  }, []);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="index" options={{ title: 'XiaoLee' }} />
      </Stack>
    </ThemeProvider>
  );
}
