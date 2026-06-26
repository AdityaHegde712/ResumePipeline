import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { UserProfile } from '../types';

export function useProfile() {
  return useQuery<UserProfile>({
    queryKey: ['profile'],
    queryFn: async () => {
      const { data } = await apiClient.get('/profile');
      return data;
    },
  });
}

export function useProfileExists() {
  return useQuery<{ exists: boolean }>({
    queryKey: ['profile', 'exists'],
    queryFn: async () => {
      const { data } = await apiClient.get('/profile/exists');
      return data;
    },
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (profile: UserProfile) => {
      const { data } = await apiClient.put('/profile', profile);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}
