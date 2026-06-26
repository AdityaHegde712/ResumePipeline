import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { Application, LLMConfig } from '../types';

export function useApplications() {
  return useQuery<Application[]>({
    queryKey: ['applications'],
    queryFn: async () => {
      const { data } = await apiClient.get('/applications');
      return data;
    },
  });
}

export function useApplication(id: string | undefined) {
  return useQuery<Application>({
    queryKey: ['applications', id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await apiClient.get(`/applications/${id}`);
      return data;
    },
  });
}

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/applications/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['applications'] });
    },
  });
}

export function useLLMConfig() {
  return useQuery<LLMConfig>({
    queryKey: ['config', 'llm'],
    queryFn: async () => {
      const { data } = await apiClient.get('/config/llm');
      return data;
    },
  });
}

export function useUpdateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (config: LLMConfig) => {
      const { data } = await apiClient.put('/config/llm', config);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config', 'llm'] });
    },
  });
}
