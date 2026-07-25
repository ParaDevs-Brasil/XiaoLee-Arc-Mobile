import React, { useState } from 'react';
import useCreateCampaign from '@/hooks/useCreateCampaign';
import { CreateCampaignRequest } from '@/interfaces';

interface CreateCampaignFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  onError: (message: string) => void; 
}

export default function CreateCampaignForm({ onSuccess, onCancel , onError }: CreateCampaignFormProps) {
  const { createCampaign, isCreating, error, success, reset } = useCreateCampaign();
  
  const [formData, setFormData] = useState<CreateCampaignRequest>({
    title: '',
    description: '',
    campaign_type: 'airdrop',
    profile_to_follow: '',
    tweet_id_to_engage: '',
    reward_token: 'USDC',
    reward_per_participant: 1,
    max_participants: 10
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    reset();
    
    try {
      await createCampaign(formData);
      if (onSuccess) {
        onSuccess();
      }
    } catch {
      onError('Failed to create campaign, try another time');
    }
  };

  const totalCost = formData.reward_per_participant * formData.max_participants;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-200 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
        🚀 Create New Campaign
      </h2>
      
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <p className="text-red-600 text-center">❌ {error}</p>
        </div>
      )}
      
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
          <p className="text-green-600 text-center">✅ Campaign created successfully!</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Título */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Campaign Title *
          </label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            required
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="Ex: Launch Campaign"
          />
        </div>

        {/* Descrição */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description *
          </label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            required
            rows={3}
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="Describe the campaign objectives..."
          />
        </div>

        {/* Campaign Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Campaign Type *
          </label>
          <select
            name="campaign_type"
            value={formData.campaign_type}
            onChange={handleInputChange}
            required
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
          >
            <option value="airdrop">Airdrop</option>
            <option value="engagement">Engagement</option>
            <option value="referral">Referral</option>
          </select>
        </div>

        {/* Profile Handle */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Twitter Profile to Follow (optional)
          </label>
          <input
            type="text"
            name="profile_to_follow"
            value={formData.profile_to_follow}
            onChange={handleInputChange}
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="Ex: @xiaolee_official"
          />
        </div>

        {/* Tweet ID */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tweet ID to Engage (optional)
          </label>
          <input
            type="text"
            name="tweet_id_to_engage"
            value={formData.tweet_id_to_engage}
            onChange={handleInputChange}
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="1234567890123456789"
          />
        </div>

        {/* Token de Recompensa */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Reward Token *
          </label>
          <input
            type="text"
            name="reward_token"
            value={formData.reward_token}
            onChange={handleInputChange}
            required
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="Ex: USDC, ETH, BTC, MATIC, etc."
          />
          <p className="text-xs text-gray-500 mt-1">
            Enter the token symbol that will be used as reward
          </p>
        </div>

        {/* Recompensa por Participante */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Reward per Participant *
          </label>
          <input
            type="number"
            name="reward_per_participant"
            value={formData.reward_per_participant}
            onChange={handleInputChange}
            required
            min="0.01"
            step="0.01"
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="1.0"
          />
        </div>

        {/* Máximo de Participantes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Maximum Participants *
          </label>
          <input
            type="number"
            name="max_participants"
            value={formData.max_participants}
            onChange={handleInputChange}
            required
            min="1"
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-transparent"
            placeholder="100"
          />
        </div>

        {/* Resumo dos Custos */}
        <div className="bg-[var(--accent-soft)] p-4 rounded-xl border border-[var(--border)]">
          <h3 className="font-semibold text-[var(--text-primary)] mb-2">💰 Cost Summary</h3>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Reward per participant:</span>
              <span className="font-medium">{formData.reward_per_participant} {formData.reward_token}</span>
            </div>
            <div className="flex justify-between">
              <span>Maximum participants:</span>
              <span className="font-medium">{formData.max_participants}</span>
            </div>
            <div className="border-t border-[var(--border)] pt-2 mt-2">
              <div className="flex justify-between font-bold text-[var(--text-primary)]">
                <span>Total required:</span>
                <span>{totalCost.toFixed(2)} {formData.reward_token}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Botões */}
        <div className="flex space-x-4 pt-4">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-colors"
            >
              Cancel
            </button>
          )}
          
          <button
            type="submit"
            disabled={isCreating}
            className={`flex-1 py-3 rounded-xl font-semibold transition-all duration-200 ${
              isCreating
                ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                : 'bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transform hover:scale-105'
            }`}
          >
            {isCreating ? (
              <span className="flex items-center justify-center space-x-2">
                <span className="animate-spin">⏳</span>
                <span>Creating...</span>
              </span>
            ) : (
              '🚀 Create Campaign'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
