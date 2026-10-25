import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  RotateCcw,
  GitBranch,
  Calendar,
  User,
  GitCommit,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { EVENT_STATUS } from '../../types';

export const CommitActivitySection = ({ events = [], onSelectEvent }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('ALL');
  const [selectedBranch, setSelectedBranch] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('desc'); // 'desc' = newest first, 'asc' = oldest first

  // Extract unique options for filter dropdowns
  const repositories = useMemo(() => {
    const set = new Set(events.map((e) => e.repository?.name || 'Unknown'));
    return Array.from(set);
  }, [events]);

  const branches = useMemo(() => {
    const set = new Set(events.map((e) => e.branch || 'unknown'));
    return Array.from(set);
  }, [events]);

  // Filter and sort events based on active controls
  const filteredEvents = useMemo(() => {
    return events
      .filter((evt) => {
        // Text Search
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchRepo = (evt.repository?.name || '').toLowerCase().includes(q);
          const matchBranch = (evt.branch || '').toLowerCase().includes(q);
          const matchSha = (evt.commit?.sha || '').toLowerCase().includes(q);
          const matchMsg = (evt.commit?.message || '').toLowerCase().includes(q);
          const matchAuthor = (evt.commit?.author?.name || '').toLowerCase().includes(q);
          const matchEventId = (evt.eventId || '').toLowerCase().includes(q);
          if (!matchRepo && !matchBranch && !matchSha && !matchMsg && !matchAuthor && !matchEventId) {
            return false;
          }
        }

        // Repo filter
        if (selectedRepo !== 'ALL' && (evt.repository?.name || '') !== selectedRepo) {
          return false;
        }

        // Branch filter
        if (selectedBranch !== 'ALL' && (evt.branch || '') !== selectedBranch) {
          return false;
        }

        // Status filter
        if (selectedStatus !== 'ALL' && (evt.status || '') !== selectedStatus) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        const timeA = new Date(a.timestamp).getTime();
        const timeB = new Date(b.timestamp).getTime();
        return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
      });
  }, [events, searchQuery, selectedRepo, selectedBranch, selectedStatus, sortOrder]);

  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    selectedRepo !== 'ALL' ||
    selectedBranch !== 'ALL' ||
    selectedStatus !== 'ALL';

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedRepo('ALL');
    setSelectedBranch('ALL');
    setSelectedStatus('ALL');
    setSortOrder('desc');
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-bold text-slate-100">Commit Event Activity</h2>
            <p className="text-xs text-slate-400">
              Audit and inspect all simulated GitHub push events ({filteredEvents.length} of {events.length} shown)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-800/80 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
              title="Toggle sort order"
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              <span>{sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}</span>
            </button>

            {hasActiveFilters && (
              <button
                onClick={handleClearFilters}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-400 hover:bg-amber-500/20 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Filters</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter Bar */}
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search commit, sha, author..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Repository Dropdown */}
          <div>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 px-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Repositories ({repositories.length})</option>
              {repositories.map((repo) => (
                <option key={repo} value={repo}>
                  {repo}
                </option>
              ))}
            </select>
          </div>

          {/* Branch Dropdown */}
          <div>
            <select
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 px-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Branches ({branches.length})</option>
              {branches.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          {/* Status Dropdown */}
          <div>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 px-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Statuses</option>
              <option value={EVENT_STATUS.SUCCESS}>Published (Success)</option>
              <option value={EVENT_STATUS.IGNORED}>Ignored (Filtered)</option>
              <option value={EVENT_STATUS.FAILED}>Rejected (Failed)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Events Table / Card Feed */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-lg">
        {filteredEvents.length === 0 ? (
          <div className="py-16 text-center">
            <Filter className="mx-auto h-10 w-10 text-slate-600 mb-3" />
            <h3 className="text-base font-bold text-slate-200">No matching events found</h3>
            <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
              {hasActiveFilters
                ? 'Try adjusting your search query or clear the active filters to see all events.'
                : 'No simulated events currently exist. Use the Push Simulator to generate events.'}
            </p>
            {hasActiveFilters && (
              <button
                onClick={handleClearFilters}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filteredEvents.map((evt) => (
              <div
                key={evt.eventId}
                onClick={() => onSelectEvent(evt)}
                className="group flex flex-col gap-3 p-4 transition-colors hover:bg-slate-800/40 cursor-pointer sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1.5 min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-mono font-bold text-emerald-400">
                      {evt.repository?.name || 'GitOps-Commit-Light'}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-300 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60">
                      <GitBranch className="w-3 h-3 text-emerald-400" />
                      {evt.branch}
                    </span>
                    <span className="font-mono text-[11px] text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      {evt.commit?.sha ? evt.commit.sha.substring(0, 7) : '0000000'}
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-slate-100 group-hover:text-emerald-300 transition-colors">
                    {evt.commit?.message || '(No commit message)'}
                  </p>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span className="inline-flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      {evt.commit?.author?.name || 'Author'}
                    </span>
                    <span>•</span>
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      {new Date(evt.timestamp).toLocaleString()}
                    </span>
                    {evt.commit?.changedFiles?.length > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-slate-500">
                          {evt.commit.changedFiles.length} file(s) modified
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3 flex-shrink-0">
                  <StatusBadge status={evt.status} />
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CommitActivitySection;

