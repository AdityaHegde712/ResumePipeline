import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from './client';
import type { ProjectEntry, MatchRequest, MatchResult } from '../types';

export function useProjects() {
  return useQuery<ProjectEntry[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      const { data } = await apiClient.get('/projects');
      return data.projects;
    },
  });
}

export function useProject(id: string | undefined) {
  return useQuery<ProjectEntry>({
    queryKey: ['projects', id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await apiClient.get(`/projects/${id}`);
      return data.project;
    },
  });
}

export function useSearchProjects() {
  return useMutation({
    mutationFn: async (query: string) => {
      const { data } = await apiClient.get('/projects/search', {
        params: { q: query },
      });
      return data.results as ProjectEntry[];
    },
  });
}

export function useRefreshProjects() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post('/projects/refresh');
      return data;
    },
  });
}

export function useMatchProjects() {
  return useMutation({
    mutationFn: async (req: MatchRequest) => {
      const { data } = await apiClient.post('/projects/match', req);
      return data.matches as MatchResult[];
    },
  });
}
