// @vitest-environment jsdom
// Wallet.test.tsx — XiaoLee Wallet (EVM) tests (replaces Stellar/Freighter suite)

import React from "react";
import { cleanup, render } from "@testing-library/react";
import { within } from "@testing-library/dom";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Wallet from "./Wallet";

vi.mock("@/hooks/useModal", () => ({
  useModal: () => ({ isOpen: true, animateIn: true, closeModal: vi.fn() }),
}));

const STORAGE_KEY = "xiaolee_evm_address";

const { connectEvmWalletMock, getEvmChainNameMock, isEvmWalletInstalledMock } = vi.hoisted(
  () => ({
    connectEvmWalletMock: vi.fn(),
    getEvmChainNameMock: vi.fn(),
    isEvmWalletInstalledMock: vi.fn(),
  }),
);

vi.mock("@/lib/evmWallet", () => ({
  connectEvmWallet: connectEvmWalletMock,
  getEvmChainName: getEvmChainNameMock,
  isEvmWalletInstalled: isEvmWalletInstalledMock,
  getStoredEvmAddress: () => localStorage.getItem(STORAGE_KEY) ?? "",
  clearStoredEvmAddress: () => localStorage.removeItem(STORAGE_KEY),
  shortEvmAddress: (address: string, front = 6, back = 4) =>
    !address || address.length <= front + back + 2
      ? address
      : `${address.slice(0, front)}…${address.slice(-back)}`,
}));

const MOCK_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678";
const MOCK_REWARDS = [{ token: "XLC", balance: 1000, priceUSD: 0.025, valueUSD: 25.0 }];

describe("Wallet — XiaoLee (EVM)", () => {
  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    isEvmWalletInstalledMock.mockReturnValue(true);
    connectEvmWalletMock.mockImplementation(async () => {
      localStorage.setItem(STORAGE_KEY, MOCK_ADDRESS);
      return MOCK_ADDRESS;
    });
    getEvmChainNameMock.mockResolvedValue("Ethereum Sepolia");
  });

  it("shows connect button when no address in localStorage", () => {
    const { container } = render(<Wallet shouldOpen balance={[]} />);
    expect(within(container).getByRole("button", { name: /Conectar Carteira/i })).toBeTruthy();
  });

  it("shows XiaoLee branding in header and footer, without Stellar references", () => {
    const { container } = render(<Wallet shouldOpen balance={[]} />);
    const screen = within(container);
    expect(screen.getAllByText(/XiaoLee/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Stellar/i)).toBeNull();
    expect(screen.queryByText(/Freighter/i)).toBeNull();
    expect(screen.queryByText(/Testnet/i)).toBeNull();
  });

  it("shows USDC and Rewards in token strip", () => {
    const { container } = render(<Wallet shouldOpen balance={[]} />);
    const screen = within(container);
    expect(screen.getByText("USDC")).toBeTruthy();
    expect(screen.getByText("Rewards")).toBeTruthy();
  });

  it("shows rewards total automatically when address already in localStorage", async () => {
    localStorage.setItem(STORAGE_KEY, MOCK_ADDRESS);
    const { container } = render(<Wallet shouldOpen balance={MOCK_REWARDS} />);
    expect((await within(container).findAllByText("$25.00")).length).toBeGreaterThan(0);
  });

  it("connects wallet and shows address on button click", async () => {
    const user = userEvent.setup();
    const { container } = render(<Wallet shouldOpen balance={[]} />);
    const screen = within(container);

    await user.click(screen.getByRole("button", { name: /Conectar Carteira/i }));

    expect(connectEvmWalletMock).toHaveBeenCalledOnce();
    expect(await screen.findByText(/Carteira conectada/i)).toBeTruthy();
    expect(screen.getByText(/0x123456…345678/i)).toBeTruthy();
  });

  it("shows error when no EVM wallet is installed", async () => {
    isEvmWalletInstalledMock.mockReturnValue(false);
    const user = userEvent.setup();
    const { container } = render(<Wallet shouldOpen balance={[]} />);
    const screen = within(container);

    await user.click(screen.getByRole("button", { name: /Conectar Carteira/i }));

    expect(await screen.findByText(/Carteira EVM não encontrada/)).toBeTruthy();
  });

  it("lists campaign reward tokens when connected", async () => {
    localStorage.setItem(STORAGE_KEY, MOCK_ADDRESS);
    const { container } = render(<Wallet shouldOpen balance={MOCK_REWARDS} />);
    const screen = within(container);
    expect(await screen.findByText("XLC")).toBeTruthy();
    expect(screen.getByText(/1[.,]000 tokens/)).toBeTruthy();
  });

  it("clears localStorage on disconnect", async () => {
    localStorage.setItem(STORAGE_KEY, MOCK_ADDRESS);
    const user = userEvent.setup();
    const { container } = render(<Wallet shouldOpen balance={[]} />);

    const disconnectBtn = container.querySelector('button[title="Desconectar"]');
    expect(disconnectBtn).toBeTruthy();
    if (disconnectBtn) await user.click(disconnectBtn);

    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
