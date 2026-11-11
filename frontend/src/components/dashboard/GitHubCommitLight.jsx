import React, { useEffect, useRef, useState } from 'react';
import { Activity, ExternalLink, GitCommit, RefreshCw } from 'lucide-react';

const REPOSITORY = 'darshan-codes-ai/GitOps-Commit-Light';
const POLL_INTERVAL_MS = 30000;
const LIGHT_DURATION_MS = 10000;

export default function GitHubCommitLight() {
  const [latestCommit, setLatestCommit] = useState(null);
  const [state, setState] = useState('checking');
  const [lastChecked, setLastChecked] = useState(null);
  const [lightOn, setLightOn] = useState(false);
  const previousSha = useRef(null);
  const lightTimer = useRef(null);

  useEffect(() => {
    let active = true;
    let inFlight = false;

    const checkForCommit = async () => {
      if (inFlight) return;
      inFlight = true;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);

      try {
        const response = await fetch(
          `https://api.github.com/repos/${REPOSITORY}/commits?per_page=1`,
          {
            headers: { Accept: 'application/vnd.github+json' },
            signal: controller.signal,
            cache: 'no-store',
          }
        );

        if (!response.ok) {
          throw new Error(`GitHub API returned HTTP ${response.status}`);
        }

        const commits = await response.json();
        const commit = commits?.[0];
        if (!commit?.sha) throw new Error('GitHub did not return a latest commit.');

        if (!active) return;

        if (previousSha.current && previousSha.current !== commit.sha) {
          setLightOn(true);
          if (lightTimer.current) clearTimeout(lightTimer.current);
          lightTimer.current = setTimeout(() => {
            if (active) setLightOn(false);
          }, LIGHT_DURATION_MS);
        }

        previousSha.current = commit.sha;
        setLatestCommit(commit);
        setState('online');
        setLastChecked(new Date());
      } catch (error) {
        if (active) setState('offline');
      } finally {
        clearTimeout(timeout);
        inFlight = false;
      }
    };

    checkForCommit();
    const interval = setInterval(checkForCommit, POLL_INTERVAL_MS);

    return () => {
      active = false;
      clearInterval(interval);
      clearTimeout(lightTimer.current);
    };
  }, []);

  const commitMessage = latestCommit?.commit?.message?.split('\n')[0] || 'Waiting for the first commit';
  const author = latestCommit?.commit?.author?.name || 'Unknown author';
  const commitUrl = latestCommit?.html_url || `https://github.com/${REPOSITORY}/commits`;

  return (
    <section className={`rounded-2xl border p-5 sm:p-6 transition-colors duration-500 ${lightOn ? 'border-emerald-400/60 bg-emerald-950/35' : 'border-slate-800 bg-slate-900/70'}`} aria-live="polite">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4 min-w-0">
          <div className={`relative flex h-20 w-20 shrink-0 items-center justify-center rounded-full border-4 transition-all duration-500 ${lightOn ? 'border-emerald-300 bg-emerald-400/15 shadow-[0_0_35px_rgba(52,211,153,0.55)]' : 'border-slate-700 bg-slate-950'}`}>
            {lightOn && <span className="absolute inset-1 rounded-full bg-emerald-400/20 animate-ping" />}
            <span className={`relative h-10 w-10 rounded-full transition-all duration-500 ${lightOn ? 'bg-emerald-300 shadow-[0_0_28px_rgba(52,211,153,0.95)]' : state === 'online' ? 'bg-slate-600' : 'bg-amber-500'}`} />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Live GitHub commit light</span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${state === 'online' ? 'bg-emerald-500/10 text-emerald-300' : state === 'offline' ? 'bg-amber-500/10 text-amber-300' : 'bg-slate-700 text-slate-300'}`}>
                {state === 'online' ? 'Watching' : state === 'offline' ? 'Connection issue' : 'Connecting'}
              </span>
            </div>
            <h3 className={`mt-1 text-xl font-black ${lightOn ? 'text-emerald-300' : 'text-white'}`}>
              {lightOn ? 'COMMIT DETECTED!' : 'Waiting for a GitHub commit'}
            </h3>
            <p className="mt-1 text-sm text-slate-400">
              {lightOn ? 'A new commit was pushed. The green light will stay on briefly.' : 'The light turns green when a new commit appears in this repository.'}
            </p>
          </div>
        </div>

        <div className="sm:text-right">
          <div className="text-xs text-slate-500">Monitored repository</div>
          <a href={`https://github.com/${REPOSITORY}`} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-indigo-300 hover:text-indigo-200">
            {REPOSITORY} <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-500 sm:justify-end">
            <RefreshCw className="h-3 w-3" />
            Checks every 30 seconds
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-2 border-t border-slate-800 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
            <GitCommit className="h-3.5 w-3.5" /> Latest GitHub commit
          </div>
          <a href={commitUrl} target="_blank" rel="noreferrer" className="mt-1 block truncate text-sm font-medium text-slate-200 hover:text-emerald-300">
            {commitMessage}
          </a>
          <p className="mt-1 text-xs text-slate-500">
            {author}{latestCommit?.sha ? ` · ${latestCommit.sha.slice(0, 7)}` : ''}
          </p>
        </div>
        <div className="shrink-0 text-xs text-slate-500 sm:text-right">
          <div className="flex items-center gap-1.5 sm:justify-end">
            <Activity className="h-3.5 w-3.5" />
            {lastChecked ? `Last checked ${lastChecked.toLocaleTimeString()}` : 'Checking GitHub...'}
          </div>
          <p className="mt-1">New commits are detected on the next poll.</p>
        </div>
      </div>
    </section>
  );
}
