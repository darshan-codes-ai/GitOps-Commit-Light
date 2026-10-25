import React, { useState, useEffect } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import OverviewSection from './components/dashboard/OverviewSection';
import CommitActivitySection from './components/activity/CommitActivitySection';
import PushSimulatorSection from './components/simulator/PushSimulatorSection';
import MqttMonitorSection from './components/mqtt/MqttMonitorSection';
import ServiceStatusSection from './components/status/ServiceStatusSection';
import AboutSection from './components/settings/AboutSection';
import EventDetailModal from './components/details/EventDetailModal';
import { getStoredEvents, storeEvent } from './services/storageService';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [events, setEvents] = useState([]);
  const [selectedEventModal, setSelectedEventModal] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Load initial events from localStorage (or seeds)
  useEffect(() => {
    const loaded = getStoredEvents();
    setEvents(loaded);
  }, []);

  // Handler when a new event is simulated
  const handleEventSimulated = (newEvent) => {
    storeEvent(newEvent);
    setEvents((prev) => [newEvent, ...prev]);
  };

  // Handler when history is cleared or restored
  const handleResetEvents = () => {
    const updated = getStoredEvents();
    setEvents(updated);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Top Header */}
      <Header 
        mobileMenuOpen={mobileMenuOpen} 
        setMobileMenuOpen={setMobileMenuOpen} 
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
            />
          )}

          {activeTab === 'mqtt' && (
            <MqttMonitorSection
              events={events}
              onSelectEvent={setSelectedEventModal}
            />
          )}

          {activeTab === 'status' && (
            <ServiceStatusSection />
          )}

          {activeTab === 'about' && (
            <AboutSection
              onResetEvents={handleResetEvents}
              eventCount={events.length}
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
          <span>GitOps Commit Light — Phase 1 Local Interactive Simulation</span>
          <span className="font-mono text-slate-600">AWS Not Connected • Local Browser Engine</span>
        </div>
      </footer>
    </div>
  );
}

