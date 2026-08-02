import { Clipboard, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useState } from 'react';

import { IconAlert, IconCheck, IconClipboard, IconClose } from '@/components/icons';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Dados para o usuário cadastrar o Arc Testnet na carteira dele.
 *
 * Existe porque **o app não consegue fazer isso sozinho**, e isso é resultado de
 * teste, não preguiça: a Rabby recusa `wallet_addEthereumChain` por
 * WalletConnect e diz isso na tela; a MetaMask recebe o pedido e nunca responde;
 * exigir a chain no handshake faz a carteira rejeitar a conexão inteira.
 *
 * Traz **todos** os campos, e não só o Chain ID. Algumas carteiras preenchem o
 * resto a partir dele (o Arc está no registro público de chains), mas isso é
 * atalho, não garantia — a Rabby, por exemplo, encontra o nome pelo Chain ID e
 * ainda assim deixa o RPC em branco.
 *
 * É pedágio de testnet: a MetaMask já traz o Arc mainnet de fábrica.
 */

/** Valores canônicos, conferidos contra `chainid.network` e `GET /v1/arc/chain-config`. */
const ARC_FIELDS: { label: string; value: string; note?: string }[] = [
  { label: 'Network name', value: 'Arc Testnet' },
  { label: 'RPC URL', value: 'https://rpc.testnet.arc.network' },
  { label: 'Chain ID', value: '5042002', note: 'not 5042 — that one is mainnet' },
  { label: 'Currency symbol', value: 'USDC', note: 'on Arc, gas is paid in USDC' },
  { label: 'Block explorer', value: 'https://testnet.arcscan.app', note: 'optional' },
];

interface ArcNetworkSheetProps {
  visible: boolean;
  onClose: () => void;
}

export function ArcNetworkSheet({ visible, onClose }: ArcNetworkSheetProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(event) => event.stopPropagation()}>
          <View style={styles.header}>
            <View style={styles.icon}>
              <IconAlert size={20} color={Colors.light.accent} />
            </View>
            <View style={styles.headerText}>
              <Text style={styles.title}>Add the Arc Testnet network</Text>
              <Text style={styles.subtitle}>One time only, in your wallet</Text>
            </View>
            <Pressable onPress={onClose} hitSlop={Spacing.two} accessibilityLabel="Close">
              <IconClose size={18} color={Colors.light.ink3} />
            </Pressable>
          </View>

          <Text style={styles.intro}>
            Your wallet doesn&apos;t know the Arc Testnet yet, and it can&apos;t sign without it. Open your
            wallet&apos;s network settings, choose to add a network manually, and fill in the fields below.
            Tap any value to copy it.
          </Text>

          <ScrollView style={styles.list} showsVerticalScrollIndicator={false}>
            {ARC_FIELDS.map((field) => (
              <CopyField key={field.label} field={field} />
            ))}
          </ScrollView>

          <Text style={styles.tip}>
            <Text style={styles.tipLabel}>Shortcut: </Text>
            some wallets can search for a network. Typing the Chain ID{' '}
            <Text style={styles.mono}>5042002</Text> finds Arc and fills in part of the form — but
            check the RPC URL, which is usually left blank.
          </Text>

          <Text style={styles.footer}>
            Once added, select the Arc network in your wallet and reconnect here.
          </Text>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function CopyField({ field }: { field: { label: string; value: string; note?: string } }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    // `Clipboard` do core do RN está deprecado e avisa no console. O substituto
    // (`expo-clipboard`) é módulo nativo e exigiria um build novo — caro demais
    // para copiar cinco strings.
    Clipboard.setString(field.value);
    setCopied(true);
    // Volta sozinho: um "copiado" permanente mente na próxima vez que o usuário
    // abre o modal.
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Pressable
      onPress={copy}
      style={({ pressed }) => [styles.field, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel={`Copy ${field.label}`}
    >
      <View style={styles.fieldText}>
        <Text style={styles.fieldLabel}>{field.label}</Text>
        <Text style={styles.fieldValue} numberOfLines={1}>
          {field.value}
        </Text>
        {field.note ? <Text style={styles.fieldNote}>{field.note}</Text> : null}
      </View>
      {copied ? (
        <IconCheck size={16} color={Colors.light.success} />
      ) : (
        <IconClipboard size={16} color={Colors.light.ink3} />
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(26,25,23,0.35)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.three,
  },
  sheet: {
    ...CardShadow,
    width: '100%',
    maxWidth: 420,
    // Teto para o modal não encostar nas bordas em tela pequena; a lista rola.
    maxHeight: '88%',
    padding: Spacing.four,
    gap: Spacing.two + 2,
    borderRadius: Radius.xl,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },

  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two + 2 },
  icon: {
    width: 40,
    height: 40,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
  },
  headerText: { flex: 1 },
  title: { fontFamily: Fonts.bold, fontSize: 16, color: Colors.light.ink },
  subtitle: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: 1 },

  intro: { fontFamily: Fonts.sans, fontSize: 13, lineHeight: 19, color: Colors.light.ink2 },

  list: { flexGrow: 0 },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingVertical: Spacing.two - 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.light.border,
  },
  pressed: { opacity: 0.6 },
  fieldText: { flex: 1 },
  fieldLabel: {
    fontFamily: Fonts.bold,
    fontSize: 10,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
  },
  fieldValue: { fontFamily: Fonts.medium, fontSize: 14, color: Colors.light.ink, marginTop: 2 },
  fieldNote: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: 1 },

  tip: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    lineHeight: 18,
    color: Colors.light.ink2,
    padding: Spacing.two,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.bg,
  },
  tipLabel: { fontFamily: Fonts.bold, color: Colors.light.ink },
  mono: { fontFamily: Fonts.bold, color: Colors.light.ink },

  footer: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    lineHeight: 18,
    color: Colors.light.ink2,
    paddingTop: Spacing.two,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.light.border,
  },
});
