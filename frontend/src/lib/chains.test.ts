import { describe, expect, it } from "vitest";
import { detectChainFromAddress, detectChainFromTx, explorerTxUrl } from "./chains";

const ARC_ADDR = "0x1234567890abcdef1234567890abcdef12345678";
const SOLANA_ADDR = "7fUAJdStEuGbc3sM84cKRL6yYaaSstyLSU4ve5oovLS7";
const STELLAR_ADDR = "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GLIFHNBRSUVRGRXBD";

const ARC_TX = "0x" + "ab".repeat(32);
const STELLAR_TX = "cd".repeat(32);
const SOLANA_TX =
  "5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW";

describe("detectChainFromAddress", () => {
  it("detects arc/EVM (0x + 40 hex)", () => {
    expect(detectChainFromAddress(ARC_ADDR)).toBe("arc");
  });
  it("detects solana (base58 32-44)", () => {
    expect(detectChainFromAddress(SOLANA_ADDR)).toBe("solana");
  });
  it("detects stellar (G + 55)", () => {
    expect(detectChainFromAddress(STELLAR_ADDR)).toBe("stellar");
  });
  it("rejects unknown formats", () => {
    expect(detectChainFromAddress("not-an-address")).toBeNull();
    expect(detectChainFromAddress("0x123")).toBeNull();
    expect(detectChainFromAddress("")).toBeNull();
    // base58 não permite 0, O, I, l
    expect(detectChainFromAddress("0OIl".repeat(10))).toBeNull();
  });
});

describe("detectChainFromTx", () => {
  it("arc tx = 0x + 64 hex", () => {
    expect(detectChainFromTx(ARC_TX)).toBe("arc");
  });
  it("stellar tx = 64 hex sem 0x", () => {
    expect(detectChainFromTx(STELLAR_TX)).toBe("stellar");
  });
  it("solana tx = assinatura base58 longa", () => {
    expect(detectChainFromTx(SOLANA_TX)).toBe("solana");
  });
});

describe("explorerTxUrl", () => {
  it("gera link do arcscan para tx arc", () => {
    expect(explorerTxUrl(ARC_TX)).toBe(`https://testnet.arcscan.app/tx/${ARC_TX}`);
  });
  it("gera link do solscan devnet para tx solana", () => {
    expect(explorerTxUrl(SOLANA_TX)).toBe(`https://solscan.io/tx/${SOLANA_TX}?cluster=devnet`);
  });
  it("gera link do stellar.expert para tx stellar", () => {
    expect(explorerTxUrl(STELLAR_TX)).toBe(
      `https://stellar.expert/explorer/testnet/tx/${STELLAR_TX}`,
    );
  });
  it("respeita chain explícita sobre a detecção", () => {
    expect(explorerTxUrl(STELLAR_TX, "arc")).toBe(`https://testnet.arcscan.app/tx/${STELLAR_TX}`);
  });
  it("retorna null quando não reconhece", () => {
    expect(explorerTxUrl("???")).toBeNull();
  });
});
