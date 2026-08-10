const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

/**
 * A Privy (via `jose`, pra verificar JWT) publica uma build própria pra
 * browser/React Native que não usa `crypto`/`util`/`zlib` do Node — mas sem
 * isto o Metro resolve pela condição "import"/"require" (a de Node) em vez
 * de "browser", e o bundle quebra tentando importar módulo que não existe no
 * runtime do React Native.
 *
 * `browser` primeiro: a ordem das condições aqui é a ordem de prioridade, e
 * é a chave "browser" que aparece primeiro no `exports` do `jose`.
 */
config.resolver.unstable_enablePackageExports = true;
config.resolver.unstable_conditionNames = ['browser', 'require', 'react-native'];

module.exports = config;
