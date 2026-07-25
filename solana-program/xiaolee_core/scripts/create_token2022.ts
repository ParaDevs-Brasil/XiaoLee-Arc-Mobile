import {
  Connection,
  Keypair,
  SystemProgram,
  Transaction,
  clusterApiUrl,
  sendAndConfirmTransaction,
} from '@solana/web3.js';
import {
  ExtensionType,
  TOKEN_2022_PROGRAM_ID,
  createInitializeMintInstruction,
  getMintLen,
  createInitializeTransferFeeConfigInstruction,
} from '@solana/spl-token';
import * as fs from 'fs';

async function main() {
  // Connect to devnet
  const connection = new Connection(clusterApiUrl('devnet'), 'confirmed');

  // Load wallet from standard location
  const secretKeyString = fs.readFileSync(process.env.HOME + '/.config/solana/id.json', 'utf8');
  const secretKey = Uint8Array.from(JSON.parse(secretKeyString));
  const payer = Keypair.fromSecretKey(secretKey);

  // Generate new keypair for the mint
  const mintKeypair = Keypair.generate();
  const decimals = 9;

  // Transfer Fee Configuration
  // Fee basis points: 50 (0.5%)
  const feeBasisPoints = 50;
  // Maximum fee: 50 XLEE
  const maxFee = BigInt(50 * Math.pow(10, decimals));

  // Determine size of the mint account with extensions
  const mintLen = getMintLen([ExtensionType.TransferFeeConfig]);

  // Minimum lamports required for exemption
  const lamports = await connection.getMinimumBalanceForRentExemption(mintLen);

  console.log(`Creating $XLEE Token-2022 mint at: ${mintKeypair.publicKey.toBase58()}`);

  const transaction = new Transaction().add(
    // 1. Create the mint account
    SystemProgram.createAccount({
      fromPubkey: payer.publicKey,
      newAccountPubkey: mintKeypair.publicKey,
      space: mintLen,
      lamports,
      programId: TOKEN_2022_PROGRAM_ID,
    }),
    // 2. Initialize the transfer fee extension
    createInitializeTransferFeeConfigInstruction(
      mintKeypair.publicKey,
      payer.publicKey, // Transfer Fee Config Authority
      payer.publicKey, // Withdraw Withheld Authority
      feeBasisPoints,
      maxFee,
      TOKEN_2022_PROGRAM_ID
    ),
    // 3. Initialize the mint
    createInitializeMintInstruction(
      mintKeypair.publicKey,
      decimals,
      payer.publicKey, // Mint Authority
      payer.publicKey, // Freeze Authority
      TOKEN_2022_PROGRAM_ID
    )
  );

  const signature = await sendAndConfirmTransaction(connection, transaction, [payer, mintKeypair]);

  console.log(`Success! Transaction Signature: ${signature}`);
  console.log(`XLEE Token Address: ${mintKeypair.publicKey.toBase58()}`);
}

main().catch(console.error);
