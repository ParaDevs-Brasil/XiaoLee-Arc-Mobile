import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { IconCoin } from '@/components/icons';

export default function TokenomicsCard() {
  const { t } = useLanguage();
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-[var(--accent)]"><IconCoin className="w-4 h-4" /></span>
        <h2 className="text-sm font-bold text-gray-700">{t('tokenomics.title')}</h2>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between py-2 border-b border-gray-100/80">
          <span className="text-xs text-gray-400 font-medium">{t('tokenomics.standard')}</span>
          <span className="text-xs text-gray-700 font-semibold">{t('tokenomics.standard_value')}</span>
        </div>

        <div className="flex items-center justify-between py-2 border-b border-gray-100/80">
          <span className="text-xs text-gray-400 font-medium">{t('tokenomics.network')}</span>
          <span className="text-xs font-semibold text-[var(--text-primary)]">{t('tokenomics.network_value')}</span>
        </div>

        <div className="flex items-center justify-between py-2 border-b border-gray-100/80">
          <span className="text-xs text-gray-400 font-medium">{t('tokenomics.transfer_fee')}</span>
          <span className="text-xs font-semibold text-[var(--text-primary)]">{t('tokenomics.fee_value')}</span>
        </div>

        <div className="pt-1">
          <p className="text-xs text-gray-400 mb-1.5">{t('tokenomics.contract_address')}</p>
          <div className="rounded-xl bg-[var(--accent-soft)] border border-[var(--border)] px-3 py-2">
            <code className="text-xs text-[var(--accent)] font-semibold block text-center">
              {t('tokenomics.awaiting_deploy')}
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}
