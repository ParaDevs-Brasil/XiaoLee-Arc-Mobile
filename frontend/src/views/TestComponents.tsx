import React, { useState } from 'react';
import { toast } from 'react-toastify';
import Wallet from '@/components/navbar/Wallet';
import Transacoes from '@/components/navbar/Transacoes';
import Historico from '@/components/navbar/Historico';
import { ThemeToggle } from '@/components/navbar/ThemeToggle';
import CampaignCard from '@/components/campaigns/CampaignCard';
import CreateCampaignForm from '@/components/campaigns/CreateCampaignForm';
import UserCampaignCard from '@/components/campaigns/UserCampaignCard';
import testDataHandling from '@/utils/testDataHandling';
import UserData from '@/components/UserData';
import { 
  TokenBalance, 
  TransactionHistoryItem, 
  Campaign, 
  UserCampaignParticipation,
} from '@/interfaces';

// Mock data
const mockTokenBalances: TokenBalance[] = [
  {
    token: 'USDC',
    balance: 1500.50,
    priceUSD: 1.00,
    valueUSD: 1500.50
  },
  {
    token: 'ETH',
    balance: 2.5,
    priceUSD: 2500.00,
    valueUSD: 6250.00
  },
  {
    token: 'BTC',
    balance: 0.1,
    priceUSD: 45000.00,
    valueUSD: 4500.00
  }
];

const mockTransactions: TransactionHistoryItem[] = [
  {
    id: 1,
    amount: '100.00',
    confirmation_blocks: 12,
    created_at: '2025-01-20T10:30:00Z',
    error_message: null,
    gas_price: '20',
    gas_used: '21000',
    recipient_twitter_handle: 'alice_crypto',
    sender_twitter_handle: 'bob_trader',
    status: 'completed',
    to_address: '0x742d35Cc6635C0532925a3b8D598544c93Eb04f4',
    token_symbol: 'USDC',
    transaction_type: 'transfer',
    tx_hash: '0x1234567890abcdef',
    updated_at: '2025-01-20T10:35:00Z',
    user_id: 1
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  },
  {
    id: 2,
    amount: '50.00',
    confirmation_blocks: 6,
    created_at: '2025-01-19T15:45:00Z',
    error_message: null,
    gas_price: '25',
    gas_used: '21000',
    recipient_twitter_handle: 'charlie_defi',
    sender_twitter_handle: 'alice_crypto',
    status: 'pending',
    to_address: '0x8ba1f109551bD432803012645Hac136c',
    token_symbol: 'ETH',
    transaction_type: 'send',
    tx_hash: '0xabcdef1234567890',
    updated_at: '2025-01-19T15:50:00Z',
    user_id: 2
  }
];

const mockCampaigns: Campaign[] = [
  {
    id: 1,
    name: 'Follow @XiaoleeAI',
    description: 'Follow our Twitter account to stay updated with the latest news and earn rewards!',
    campaign_type: 'follow',
    completed_participants: 150,
    created_at: '2025-01-15T08:00:00Z',
    creator_twitter_user_id: '123456789',
    max_participants: 1000,
    profile_to_follow: 'XiaoleeAI',
    reward_per_participant: 10,
    reward_pool: 10000,
    reward_token: 'USDC',
    status: 'active',
    tweet_id_to_engage: null
  },
  {
    id: 2,
    name: 'Retweet Our Launch',
    description: 'Help us spread the word by retweeting our launch announcement!',
    campaign_type: 'retweet',
    completed_participants: 89,
    created_at: '2025-01-14T10:00:00Z',
    creator_twitter_user_id: '123456789',
    max_participants: 500,
    profile_to_follow: null,
    reward_per_participant: 25,
    reward_pool: 12500,
    reward_token: 'ETH',
    status: 'active',
    tweet_id_to_engage: '1234567890123456789'
  }
];

const mockUserCampaigns: UserCampaignParticipation[] = [
  {
    id: 1,
    name: 'Follow @XiaoleeAI',
    description: 'Follow our Twitter account to stay updated with the latest news and earn rewards!',
    reward_token: 'USDC',
    reward_per_participant: 10,
    campaign_type: 'twitter_follow',
    participation_status: 'enrolled',
    tasks_verified_at: null,
    tasks_claimed: false
  },
  {
    id: 2,
    name: 'Beta Tester Program',
    description: 'Test our new features and provide feedback to earn exclusive rewards!',
    reward_token: 'ETH',
    reward_per_participant: 50,
    campaign_type: 'beta_test',
    participation_status: 'tasks_verified',
    tasks_verified_at: '2025-01-19T14:30:00Z',
    tasks_claimed: false
  },
  {
    id: 3,
    name: 'Community Ambassador',
    description: 'Help grow our community and earn ongoing rewards!',
    reward_token: 'USDC',
    reward_per_participant: 100,
    campaign_type: 'ambassador',
    participation_status: 'paid',
    tasks_verified_at: '2025-01-17T09:15:00Z',
    tasks_claimed: true
  }
];

const TestComponents: React.FC = () => {
  const [walletOpen, setWalletOpen] = useState(false);
  const [transacoesOpen, setTransacoesOpen] = useState(false);
  const [historicoOpen, setHistoricoOpen] = useState(false);

  // Mock campaign actions
  const handleJoinCampaign = async (campaignId: number) => {
    console.log('Joining campaign:', campaignId);
    toast.info('🚀 Joining campaign...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    toast.success('✅ Successfully joined campaign!');
    return { success: true, message: 'Successfully joined campaign!' };
  };

  const handleVerifyTasks = async (campaignId: number) => {
    console.log('Verifying tasks for campaign:', campaignId);
    toast.info('🔍 Verifying tasks...');
    await new Promise(resolve => setTimeout(resolve, 3000));
    toast.success('✅ Tasks verified successfully!');
    return { success: true, message: 'Tasks verified successfully!' };
  };

  const handleClaimReward = async (campaignId: number) => {
    console.log('Claiming reward for campaign:', campaignId);
    toast.info('💎 Claiming reward...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    toast.success('🎉 Reward claimed successfully!', {
      autoClose: 5000
    });
    return { success: true, message: 'Reward claimed successfully!' };
  };

  const handleCreateCampaign = () => {
    console.log('Campaign creation completed');
    toast.success('✨ Campaign created successfully!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 bg-clip-text text-transparent mb-4">
            🧪 Component Test Page
          </h1>
          <p className="text-gray-600 text-lg">
            Test all Xiaolee components with mock dataa
          </p>
          <div className="flex justify-center mt-4">
            <ThemeToggle />
          </div>
        </div>

        {/* Data Handling Test */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
            <span className="mr-2">🧪</span>
            Data Handling Test (Your JSON Format)
          </h2>
          <div className="text-center mb-6">
            <button
              onClick={() => {
                try {
                  const testResult = testDataHandling();
                  toast.success('✅ Data handling test completed! Check console for details.');
                  console.log("🎉 Test completed successfully:", testResult);
                } catch (error) {
                  toast.error('❌ Data handling test failed! Check console for details.');
                  console.error("💥 Test failed:", error);
                }
              }}
              className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-8 py-4 rounded-xl hover:scale-105 transition-transform text-lg font-bold shadow-lg"
            >
              🧪 Test Your JSON Data Format 🧪
            </button>
            <p className="text-gray-600 mt-3">
              This will load your provided JSON structure into UserData and test all components
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => {
                UserData.clearData();
                toast.info('🧹 UserData cleared');
              }}
              className="bg-gradient-to-r from-red-500 to-pink-500 text-white px-4 py-2 rounded-lg hover:scale-105 transition-transform"
            >
              🧹 Clear UserData
            </button>
            <button
              onClick={() => {
                const userData = UserData.getUserData();
                console.log("📊 Current UserData:", userData);
                toast.info('📊 Current UserData logged to console');
              }}
              className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-4 py-2 rounded-lg hover:scale-105 transition-transform"
            >
              📊 Log Current UserData
            </button>
          </div>
        </div>

        {/* Navigation Components */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
            <span className="mr-2">🧭</span>
            Navigation Components
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <h3 className="font-semibold mb-3">Wallet Component</h3>
              <button
                onClick={() => setWalletOpen(true)}
                className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-3 rounded-xl hover:scale-105 transition-transform"
              >
                💰 Open Wallet
              </button>
            </div>
            <div className="text-center">
              <h3 className="font-semibold mb-3">Transactions Component</h3>
              <button
                onClick={() => setTransacoesOpen(true)}
                className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-6 py-3 rounded-xl hover:scale-105 transition-transform"
              >
                💸 Open Transactions
              </button>
            </div>
            <div className="text-center">
              <h3 className="font-semibold mb-3">History Component</h3>
              <button
                onClick={() => setHistoricoOpen(true)}
                className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-xl hover:scale-105 transition-transform"
              >
                📚 Open History
              </button>
            </div>
          </div>
        </div>

        {/* Toast Notifications Testing */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
            <span className="mr-2">🔔</span>
            Toast Notifications Testing
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => {
                // Comprehensive toast test sequence
                toast.info('🚀 Starting toast test sequence...');
                
                setTimeout(() => {
                  toast.success('✅ Step 1: Success notification working!');
                }, 1000);
                
                setTimeout(() => {
                  toast.warning('⚠️ Step 2: Warning notification working!');
                }, 2000);
                
                setTimeout(() => {
                  toast.error('❌ Step 3: Error notification working!');
                }, 3000);
                
                setTimeout(() => {
                  const loadingId = toast.loading('⏳ Step 4: Testing loading...');
                  setTimeout(() => {
                    toast.update(loadingId, {
                      render: '🎉 Step 5: Loading → Success transition complete!',
                      type: 'success',
                      isLoading: false,
                      autoClose: 3000
                    });
                  }, 2000);
                }, 4000);
                
                setTimeout(() => {
                  toast('🧪 Test sequence completed! All toasts working perfectly! 🎊', {
                    style: {
                      background: 'linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4)',
                      color: 'white',
                      fontWeight: 'bold'
                    },
                    autoClose: 5000
                  });
                }, 8000);
              }}
              className="col-span-2 md:col-span-4 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white px-6 py-4 rounded-xl hover:scale-105 transition-transform text-lg font-bold shadow-lg"
            >
              🧪 RUN FULL TOAST TEST SEQUENCE 🧪
            </button>
            
            <button
              onClick={() => toast.success('🎉 Success message! Everything worked perfectly!')}
              className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              ✅ Success Toast
            </button>
            <button
              onClick={() => toast.error('❌ Error message! Something went wrong.')}
              className="bg-gradient-to-r from-red-500 to-pink-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              🚫 Error Toast
            </button>
            <button
              onClick={() => toast.warning('⚠️ Warning message! Please check this.')}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              ⚠️ Warning Toast
            </button>
            <button
              onClick={() => toast.info('ℹ️ Info message! Here\'s some information.')}
              className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              ℹ️ Info Toast
            </button>
            <button
              onClick={() => toast.success('🎊 Campaign completed!', { autoClose: 5000 })}
              className="bg-gradient-to-r from-purple-500 to-indigo-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              🎊 Long Toast (5s)
            </button>
            <button
              onClick={() => toast.loading('🔄 Processing your request...', { autoClose: false })}
              className="bg-gradient-to-r from-gray-500 to-slate-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              🔄 Loading Toast
            </button>
            <button
              onClick={() => {
                const toastId = toast.loading('⏳ Campaign joining...');
                setTimeout(() => {
                  toast.update(toastId, {
                    render: '✅ Successfully joined campaign!',
                    type: 'success',
                    isLoading: false,
                    autoClose: 3000
                  });
                }, 2000);
              }}
              className="bg-gradient-to-r from-teal-500 to-green-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              🔄➡️✅ Update Toast
            </button>
            <button
              onClick={() => toast('🌈 Custom colorful message!', {
                style: {
                  background: 'linear-gradient(45deg, #ff6b6b, #4ecdc4)',
                  color: 'white'
                }
              })}
              className="bg-gradient-to-r from-pink-500 to-cyan-500 text-white px-4 py-3 rounded-xl hover:scale-105 transition-transform text-sm"
            >
              🌈 Custom Style
            </button>
          </div>
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              <strong>💡 Toast Testing:</strong> Try different toast types to test the notification system. 
              Toasts appear in the top-right corner and auto-dismiss after 3 seconds (unless specified otherwise).
            </p>
          </div>
        </div>

        {/* Campaign Components */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
            <span className="mr-2">🚀</span>
            Campaign Components
          </h2>
          
          {/* Public Campaigns */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold mb-4">Public Campaigns</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {mockCampaigns.map((campaign) => (
                <CampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onJoin={handleJoinCampaign}
                  onVerify={handleVerifyTasks}
                  onClaim={handleClaimReward}
                  isJoining={() => false}
                  isVerifying={() => false}
                  isClaiming={() => false}
                />
              ))}
            </div>
          </div>

          {/* User Campaigns */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold mb-4">User Campaigns</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {mockUserCampaigns.map((campaign) => (
                <UserCampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onVerify={handleVerifyTasks}
                  onClaim={handleClaimReward}
                  isVerifying={() => false}
                  isClaiming={() => false}
                />
              ))}
            </div>
          </div>

          {/* Create Campaign Form */}
          <div>
            <h3 className="text-xl font-semibold mb-4">Create Campaign Form</h3>
            <div className="bg-gray-50 rounded-xl p-6">
              <CreateCampaignForm
                onSuccess={handleCreateCampaign}
                onCancel={() => console.log('Campaign creation cancelled')}
                onError={(error) => toast.error(`Error creating campaign: ${error}`)}
              />
            </div>
          </div>
        </div>

        {/* Mock Data Preview */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
            <span className="mr-2">📊</span>
            Mock Data Preview
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <h3 className="font-semibold mb-3">Token Balances</h3>
              <div className="bg-gray-50 rounded-lg p-4 text-sm">
                <pre>{JSON.stringify(mockTokenBalances, null, 2)}</pre>
              </div>
            </div>
            <div>
              <h3 className="font-semibold mb-3">Transactions</h3>
              <div className="bg-gray-50 rounded-lg p-4 text-sm max-h-64 overflow-y-auto">
                <pre>{JSON.stringify(mockTransactions, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>

        {/* Component Instances */}
        <Wallet
          balance={mockTokenBalances}
          shouldOpen={walletOpen}
          onClose={() => setWalletOpen(false)}
        />

        <Transacoes
          transactions={mockTransactions}
          balance={mockTokenBalances}
          shouldOpen={transacoesOpen}
          onClose={() => setTransacoesOpen(false)}
        />

        <Historico
          shouldOpen={historicoOpen}
          onClose={() => setHistoricoOpen(false)}
        />
      </div>
    </div>
  );
};

export default TestComponents;
