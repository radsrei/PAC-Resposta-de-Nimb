import { TreasureCreature, TreasureGroupItem, TreasureGroupResult } from '../types';
import { http } from './http';

/**
 * Sorteio de tesouro pelas tabelas do livro (Tormenta20, Capítulo 8).
 * Exige um livro liberado com as tabelas de tesouro (sem ele o backend responde 428).
 */
export const treasureApiService = {
  /** Criaturas do livro com ND e tipo de tesouro da ficha. */
  async listCreatures(): Promise<TreasureCreature[]> {
    return http.get<TreasureCreature[]>('/api/tesouro/criaturas?limit=200');
  },

  /** Sorteia o tesouro de cada unidade das criaturas e grava no histórico. */
  async rollGroup(creatures: TreasureGroupItem[]): Promise<TreasureGroupResult> {
    return http.post<TreasureGroupResult>('/api/tesouro/sortear-grupo', { creatures });
  },
};
