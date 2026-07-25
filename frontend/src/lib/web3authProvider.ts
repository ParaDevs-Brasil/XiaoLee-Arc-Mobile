// Module-level singleton that persists the Web3Auth provider across components.
// Set on login, cleared on logout. Lost on page refresh (re-login required to swap again).

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _provider: any = null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function setWeb3AuthProvider(provider: any) {
  _provider = provider;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function getWeb3AuthProvider(): any {
  return _provider;
}

export function clearWeb3AuthProvider() {
  _provider = null;
}
