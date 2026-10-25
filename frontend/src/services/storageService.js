/**
 * Safe LocalStorage persistence service for simulated GitOps events.
 * Handles quota limits, invalid data corruption, and initial seeding gracefully.
 */

import { INITIAL_SEED_EVENTS } from '../data/seedEvents';

const STORAGE_KEY = 'gitops_commit_light_events';

export const storageService = {
  /**
   * Load events from localStorage. Falls back to seed events if empty or corrupted.
   */
  getEvents: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        // Initial seed
        localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SEED_EVENTS));
        return INITIAL_SEED_EVENTS;
      }
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
      // If parsed was an empty array, return it as valid user-cleared state
      if (Array.isArray(parsed)) {
        return parsed;
      }
      return INITIAL_SEED_EVENTS;
    } catch (err) {
      console.warn('StorageService: Failed to parse localStorage events, falling back to seed data.', err);
      return INITIAL_SEED_EVENTS;
    }
  },

  /**
   * Save events array to localStorage with error handling for quota/privacy restrictions.
   */
  saveEvents: (events) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
      return true;
    } catch (err) {
      console.error('StorageService: Failed to save events to localStorage (quota or privacy error).', err);
      return false;
    }
  },

  /**
   * Add a new event to the top of the event list and persist.
   */
  addEvent: (newEvent) => {
    const current = storageService.getEvents();
    const updated = [newEvent, ...current];
    storageService.saveEvents(updated);
    return updated;
  },

  /**
   * Clear all stored events.
   */
  clearEvents: () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
      return [];
    } catch (err) {
      console.error('StorageService: Failed to clear events from localStorage.', err);
      return [];
    }
  },

  /**
   * Restore initial seed events.
   */
  restoreSeedEvents: () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SEED_EVENTS));
      return INITIAL_SEED_EVENTS;
    } catch (err) {
      console.error('StorageService: Failed to restore seed events.', err);
      return INITIAL_SEED_EVENTS;
    }
  }
};

export const getStoredEvents = () => storageService.getEvents();
export const saveEvents = (events) => storageService.saveEvents(events);
export const storeEvent = (event) => storageService.addEvent(event);
export const clearStoredEvents = () => storageService.clearEvents();
export const restoreSeedEvents = () => storageService.restoreSeedEvents();
export default storageService;

