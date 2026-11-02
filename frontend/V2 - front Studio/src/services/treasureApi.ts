import { TreasureCreature, TreasureGroupItem, TreasureGroupResult, TreasureLookup } from '../types';
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

  /**
   * Consulta nas tabelas com os resultados rolados na mesa (na ordem pedida).
   * Devolve a próxima rolagem que falta ou o tesouro pronto (gravado no histórico).
   */
  async lookup(creature: string, values: number[]): Promise<TreasureLookup> {
    return http.post<TreasureLookup>('/api/tesouro/consultar', { creature, values });
  },
};
