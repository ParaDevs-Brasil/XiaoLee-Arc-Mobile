import { useCallback, useEffect, useState } from 'react';
import api from '@/api/api';
import UserData from '@/components/UserData';

export interface NotificationItem {
  id: number;
  channel: string;
  title: string;
  body: string;
  status: string;
  related_signature?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string;
}

interface NotificationsResponse {
  success: boolean;
  notifications: NotificationItem[];
}

export const useNotifications = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ackLoadingStates, setAckLoadingStates] = useState<Record<number, boolean>>({});

  const fetchNotifications = useCallback(async () => {
    const sessionId = UserData.getOrCreateDevnetSession();
    if (!sessionId) {
      setNotifications([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const headers = {
        Authorization: `Bearer ${sessionId}`,
      };

      const response = await api.get<NotificationsResponse>(`/v1/notifications/me`, { headers });
      if (response.data.success) {
        setNotifications(response.data.notifications || []);
      } else {
        setNotifications([]);
        setError('Falha ao buscar notificações');
      }
    } catch (err) {
      console.error('❌ Erro ao buscar notificações:', err);
      setNotifications([]);
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  }, []);

  const ackNotification = useCallback(async (notificationId: number) => {
    const sessionId = UserData.getOrCreateDevnetSession();
    if (!sessionId) {
      throw new Error('Nao foi possivel iniciar sessao Devnet');
    }

    setAckLoadingStates((prev) => ({ ...prev, [notificationId]: true }));
    try {
      await api.post(`/v1/notifications/${notificationId}/ack`, undefined, {
        headers: {
          Authorization: `Bearer ${sessionId}`,
        },
      });
      await fetchNotifications();
    } catch (err) {
      console.error('❌ Erro ao reconhecer notificação:', err);
      throw err;
    } finally {
      setAckLoadingStates((prev) => ({ ...prev, [notificationId]: false }));
    }
  }, [fetchNotifications]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  return {
    notifications,
    loading,
    error,
    refetch: fetchNotifications,
    ackNotification,
    isAckLoading: (notificationId: number) => ackLoadingStates[notificationId] || false,
  };
};

export default useNotifications;