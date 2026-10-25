import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import OverviewSection from './components/dashboard/OverviewSection';
import CommitActivitySection from './components/activity/CommitActivitySection';
import PushSimulatorSection from './components/simulator/PushSimulatorSection';
import MqttMonitorSection from './components/mqtt/MqttMonitorSection';
import ServiceStatusSection from './components/status/ServiceStatusSection';
import AboutSection from './components/settings/AboutSection';
import EventDetailModal from './components/details/EventDetailModal';
import { getStoredEvents, storeEvent, saveEvents, clearStoredEvents, restoreSeedEvents } from './services/storageService';
import apiClient from './services/apiClient';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [events, setEvents] = useState([]);
  const [selectedEventModal, setSelectedEventModal] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'offline'
  const [isSyncing, setIsSyncing] = useState(false);

  // Initialize and check backend connection
  const loadData = useCallback(async () => {
    setIsSyncing(true);
    try {
      const health = await apiClient.checkHealth();
      if (health.success && health.data?.status === 'healthy') {
        setBackendStatus('connected');
        const eventsRes = await apiClient.getEvents();
        if (eventsRes.success && Array.isArray(eventsRes.data)) {
          setEvents(eventsRes.data);
          saveEvents(eventsRes.data);
          setIsSyncing(false);
          return;
        }
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
    }

    // Fallback to local storage if backend is offline
    const localEvents = getStoredEvents();
    setEvents(localEvents);
    setIsSyncing(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handler when a new event is simulated
  const handleEventSimulated = (newEvent) => {
    storeEvent(newEvent);
    setEvents((prev) => [newEvent, ...prev]);
  };

  // Handler when history is cleared or restored
  const handleResetEvents = async (action = 'restore') => {
    setIsSyncing(true);
    if (backendStatus === 'connected') {
      try {
        await apiClient.resetEvents(action);
        const refreshed = await apiClient.getEvents();
        if (refreshed.success && Array.isArray(refreshed.data)) {
          setEvents(refreshed.data);
          saveEvents(refreshed.data);
          setIsSyncing(false);
          return;
        }
      } catch (err) {
        console.warn('Backend reset failed, using local storage fallback', err);
      }
    }

    // Local fallback
    if (action === 'clear') {
      clearStoredEvents();
      setEvents([]);
    } else {
      const restored = restoreSeedEvents();
      setEvents(restored);
    }
    setIsSyncing(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Top Header */}
      <Header 
        mobileMenuOpen={mobileMenuOpen} 
        setMobileMenuOpen={setMobileMenuOpen}
        backendStatus={backendStatus}
        onRefresh={loadData}
        isSyncing={isSyncing}
      />

      {/* Main Layout Area */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Navigation Sidebar */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={(tab) => {
            setActiveTab(tab);
            setMobileMenuOpen(false);
          }}
          eventCount={events.length}
          mobileOpen={mobileMenuOpen}
        />

        {/* Main Content View */}
        <main className="flex-1 min-w-0">
          {activeTab === 'overview' && (
            <OverviewSection
              events={events}
              onNavigate={setActiveTab}
              onSelectEvent={setSelectedEventModal}
              backendStatus={backendStatus}
            />
          )}

          {activeTab === 'activity' && (
            <CommitActivitySection
              events={events}
              onSelectEvent={setSelectedEventModal}
            />
          )}

          {activeTab === 'simulator' && (
            <PushSimulatorSection
              onEventSimulated={handleEventSimulated}
              onViewDetails={setSelectedEventModal}
              backendStatus={backendStatus}
            />
          )}

          {activeTab === 'mqtt' && (
            <MqttMonitorSection
              events={events}
              onSelectEvent={setSelectedEventModal}
            />
          )}

          {activeTab === 'status' && (
            <ServiceStatusSection backendStatus={backendStatus} />
          )}

          {activeTab === 'about' && (
            <AboutSection
              onResetEvents={handleResetEvents}
              eventCount={events.length}
              backendStatus={backendStatus}
            />
          )}
        </main>
      </div>

      {/* Global Event Detail Modal */}
      <EventDetailModal
        event={selectedEventModal}
        isOpen={!!selectedEventModal}
        onClose={() => setSelectedEventModal(null)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>GitOps Commit Light — Local Interactive Simulation & Integration</span>
          <span className="font-mono text-slate-600">
            {backendStatus === 'connected' ? 'Connected to Local Python API Server (Port 8000)' : 'Client-Side Offline Simulation'}
          </span>
        </div>
      </footer>
    </div>
  );
}
