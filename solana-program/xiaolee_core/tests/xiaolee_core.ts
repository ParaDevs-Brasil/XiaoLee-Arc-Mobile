import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { XiaoleeCore } from "../target/types/xiaolee_core";
import { expect } from "chai";

describe("xiaolee_core", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.XiaoleeCore as Program<XiaoleeCore>;
  const twitterId = "123456789";

  // Gerar um hacker (usuário normal)
  const hacker = anchor.web3.Keypair.generate();

  // PDA derivation
  const [globalConfigPda] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("global_config")],
    program.programId
  );

  const [userPda] = anchor.web3.PublicKey.findProgramAddressSync(
    [Buffer.from("user"), Buffer.from(twitterId)],
    program.programId
  );

  before(async () => {
    // Airdrop pro hacker conseguir pagar transações
    const sig = await provider.connection.requestAirdrop(hacker.publicKey, 1000000000);
    await provider.connection.confirmTransaction(sig);
  });

  it("Initializes Global Config with Admin", async () => {
    await program.methods
      .initializeGlobal()
      .accounts({
        globalConfig: globalConfigPda,
        admin: provider.wallet.publicKey, // O deployer (nosso backend) será o admin
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const config = await program.account.globalConfig.fetch(globalConfigPda);
    expect(config.admin.toBase58()).to.equal(provider.wallet.publicKey.toBase58());
  });

  it("Initializes User PDA", async () => {
    await program.methods
      .initializeUser(twitterId)
      .accounts({
        userState: userPda,
        user: provider.wallet.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const account = await program.account.userState.fetch(userPda);
    expect(account.twitterId).to.equal(twitterId);
    expect(account.swapCount.toNumber()).to.equal(0);
  });

  it("Admin can record a swap successfully", async () => {
    const volume = new anchor.BN(1000000); // 1 USDC

    await program.methods
      .recordSwap(volume)
      .accounts({
        globalConfig: globalConfigPda,
        userState: userPda,
        admin: provider.wallet.publicKey, // Assinatura válida do admin
      })
      .rpc();

    const account = await program.account.userState.fetch(userPda);
    expect(account.swapCount.toNumber()).to.equal(1);
    expect(account.totalVolume.toNumber()).to.equal(1000000);
  });

  it("Hacker CANNOT record a swap (Unauthorized)", async () => {
    const volume = new anchor.BN(9999999999); // Hacker tentando inflar dados

    try {
      await program.methods
        .recordSwap(volume)
        .accounts({
          globalConfig: globalConfigPda,
          userState: userPda,
          admin: hacker.publicKey, // Assinatura inválida
        })
        .signers([hacker])
        .rpc();
      
      expect.fail("A transação devia ter falhado por Unauthorized!");
    } catch (e: any) {
      expect(e.message).to.include("Unauthorized");
    }
  });

  it("Prevents strings larger than 32 chars in PDA seeds (Solana Limit)", async () => {
    const hugeString = "a".repeat(33); // Solana seed limit is 32 bytes

    try {
      const [badPda] = anchor.web3.PublicKey.findProgramAddressSync(
        [Buffer.from("user"), Buffer.from(hugeString)],
        program.programId
      );
      
      await program.methods
        .initializeUser(hugeString)
        .accounts({
          userState: badPda,
          user: provider.wallet.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();
      expect.fail("Devia ter falhado por Seed limits!");
    } catch (e: any) {
      expect(e.message).to.include("Max seed length exceeded");
    }
  });
});
