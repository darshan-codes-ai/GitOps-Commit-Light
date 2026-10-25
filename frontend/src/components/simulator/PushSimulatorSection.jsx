import React, { useState } from 'react';
import {
  PlayCircle,
  RotateCcw,
  Sparkles,
  GitCommit,
  GitBranch,
  FileText,
  User,
  Mail,
  FolderGit2,
  CheckCircle2,
  AlertCircle,
  Radio,
  ArrowRight
} from 'lucide-react';
import { simulatorService, generateCommitSha } from '../../services/simulatorService';
import { JsonViewer } from '../common/JsonViewer';

export const PushSimulatorSection = ({ 
  onEventCreated, 
  onEventSimulated, 
  onSelectEvent, 
  onViewDetails 
}) => {
  const triggerCreated = onEventSimulated || onEventCreated;
  const triggerSelect = onViewDetails || onSelectEvent;
  const defaultValues = {
    owner: 'darshan-codes-ai',
    repoName: 'GitOps-Commit-Light',
    branch: 'main',
    commitSha: generateCommitSha(),
    commitMessage: 'feat: add automated commit alert pipeline subscriber',
    authorName: 'Darshan Kumar',
    authorEmail: 'darshan@example.com',
    changedFilesText: 'README.md\nk8s/deployment.yaml\nfirmware/esp32/main.ino',
    isDeleted: false,
    isMalformed: false,
  };

  const [formData, setFormData] = useState(defaultValues);
  const [errors, setErrors] = useState({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [lastResult, setLastResult] = useState(null);

  // Form field change handler
  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  // Preset loaders for easy demonstration
  const handleLoadPreset = (type) => {
    if (type === 'valid-feature') {
      setFormData({
        ...defaultValues,
        commitSha: generateCommitSha(),
        commitMessage: 'feat: add automated commit alert pipeline subscriber',
        branch: 'main',
        isDeleted: false,
        isMalformed: false,
      });
    } else if (type === 'valid-fix') {
      setFormData({
        ...defaultValues,
        commitSha: generateCommitSha(),
        commitMessage: 'fix: handle transient MQTT broker reconnect in ESP32 subscriber',
        branch: 'main',
        isDeleted: false,
        isMalformed: false,
      });
    } else if (type === 'non-monitored') {
      setFormData({
        ...defaultValues,
        commitSha: generateCommitSha(),
        commitMessage: 'chore(deps): bump vite from 5.4.8 to 5.4.9 in frontend',
        branch: 'feature/dep-update-vite',
        isDeleted: false,
        isMalformed: false,
      });
    } else if (type === 'branch-deletion') {
      setFormData({
        ...defaultValues,
        commitSha: '0000000000000000000000000000000000000000',
        commitMessage: '(Branch deletion)',
        branch: 'temp/experimental-cache',
        isDeleted: true,
        isMalformed: false,
      });
    } else if (type === 'malformed') {
      setFormData({
        ...defaultValues,
        commitMessage: '',
        isMalformed: true,
      });
    }
    setErrors({});
    setLastResult(null);
  };

  const validate = () => {
    const errs = {};
    if (!formData.isMalformed) {
      if (!formData.repoName.trim()) errs.repoName = 'Repository name is required';
      if (!formData.branch.trim()) errs.branch = 'Branch name is required';
      if (!formData.isDeleted && !formData.commitMessage.trim()) errs.commitMessage = 'Commit message is required';
      if (!formData.authorName.trim()) errs.authorName = 'Author name is required';
      if (!formData.commitSha.trim()) errs.commitSha = 'Commit SHA is required';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSimulate = (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsProcessing(true);
    setActiveStep(1);

    const changedFiles = formData.changedFilesText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    // Run stepped simulation
    setTimeout(() => {
      setActiveStep(2);
      setTimeout(() => {
        setActiveStep(3);
        setTimeout(() => {
          setActiveStep(4);
          setTimeout(() => {
            setActiveStep(5);

            const result = simulatorService.simulatePushEvent({
              ...formData,
              changedFiles,
            });

            setIsProcessing(false);
            setLastResult(result);
            if (triggerCreated) {
              triggerCreated(result);
            }
          }, 200);
        }, 200);
      }, 200);
    }, 200);
  };

  const handleReset = () => {
    setFormData({
      ...defaultValues,
      commitSha: generateCommitSha(),
    });
    setErrors({});
    setLastResult(null);
    setActiveStep(0);
  };

  return (
    <div className="space-y-6">
      {/* Header card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <PlayCircle className="w-5 h-5 text-emerald-400" />
              <span>GitHub Push Webhook Simulator</span>
            </h2>
            <p className="text-xs text-slate-400">
              Generate simulated push events, observe the Lambda processing pipeline, and inspect the emitted MQTT Schema v1 payload.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>
        </div>

        {/* Quick Presets Bar */}
        <div className="mt-4 pt-4 border-t border-slate-800/80">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Load Quick Simulation Scenarios:</span>
          </span>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleLoadPreset('valid-feature')}
              type="button"
              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20 transition-colors"
            >
              Feature Push (main) &rarr; Publish
            </button>
            <button
              onClick={() => handleLoadPreset('valid-fix')}
              type="button"
              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20 transition-colors"
            >
              Hotfix Push (main) &rarr; Publish
            </button>
            <button
              onClick={() => handleLoadPreset('non-monitored')}
              type="button"
              className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-300 hover:bg-amber-500/20 transition-colors"
            >
              Feature Branch &rarr; Ignored
            </button>
            <button
              onClick={() => handleLoadPreset('branch-deletion')}
              type="button"
              className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-300 hover:bg-amber-500/20 transition-colors"
            >
              Branch Deletion &rarr; Ignored
            </button>
            <button
              onClick={() => handleLoadPreset('malformed')}
              type="button"
              className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-medium text-rose-300 hover:bg-rose-500/20 transition-colors"
            >
              Malformed Signature &rarr; Rejected (400)
            </button>
          </div>
        </div>
      </div>

      {/* Main Form and Output Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Form Column */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-4 pb-2 border-b border-slate-800/80">
            Commit & Webhook Parameters
          </h3>

          <form onSubmit={handleSimulate} className="space-y-4">
            {/* Repository Info */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Repository Owner
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={formData.owner}
                    onChange={(e) => handleChange('owner', e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Repository Name *
                </label>
                <div className="relative">
                  <FolderGit2 className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={formData.repoName}
                    onChange={(e) => handleChange('repoName', e.target.value)}
                    className={`w-full rounded-lg border bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 focus:outline-none focus:ring-1 ${
                      errors.repoName ? 'border-rose-500 focus:ring-rose-500' : 'border-slate-800 focus:border-emerald-500 focus:ring-emerald-500'
                    }`}
                  />
                </div>
                {errors.repoName && <p className="mt-1 text-[11px] text-rose-400">{errors.repoName}</p>}
              </div>
            </div>

            {/* Branch and Commit SHA */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Branch Name *
                </label>
                <div className="relative">
                  <GitBranch className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={formData.branch}
                    onChange={(e) => handleChange('branch', e.target.value)}
                    className={`w-full rounded-lg border bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 focus:outline-none focus:ring-1 ${
                      errors.branch ? 'border-rose-500 focus:ring-rose-500' : 'border-slate-800 focus:border-emerald-500 focus:ring-emerald-500'
                    }`}
                  />
                </div>
                {errors.branch && <p className="mt-1 text-[11px] text-rose-400">{errors.branch}</p>}
                <p className="mt-1 text-[11px] text-slate-500">Monitored branch is &apos;main&apos;</p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Commit SHA (40-hex) *
                  </label>
                  <button
                    type="button"
                    onClick={() => handleChange('commitSha', generateCommitSha())}
                    className="text-[11px] text-emerald-400 hover:text-emerald-300"
                  >
                    Random SHA
                  </button>
                </div>
                <div className="relative">
                  <GitCommit className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={formData.commitSha}
                    onChange={(e) => handleChange('commitSha', e.target.value)}
                    className="w-full font-mono rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>
            </div>

            {/* Commit Message */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Commit Message *
              </label>
              <textarea
                rows="2"
                value={formData.commitMessage}
                onChange={(e) => handleChange('commitMessage', e.target.value)}
                placeholder="e.g. feat: add automated commit alert pipeline subscriber"
                className={`w-full rounded-lg border bg-slate-950 p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-1 ${
                  errors.commitMessage ? 'border-rose-500 focus:ring-rose-500' : 'border-slate-800 focus:border-emerald-500 focus:ring-emerald-500'
                }`}
              />
              {errors.commitMessage && <p className="mt-1 text-[11px] text-rose-400">{errors.commitMessage}</p>}
            </div>

            {/* Author Name and Email */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Author Name *
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={formData.authorName}
                    onChange={(e) => handleChange('authorName', e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Author Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="email"
                    value={formData.authorEmail}
                    onChange={(e) => handleChange('authorEmail', e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>
            </div>

            {/* Changed Files */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Changed Files (one per line)</span>
              </label>
              <textarea
                rows="3"
                value={formData.changedFilesText}
                onChange={(e) => handleChange('changedFilesText', e.target.value)}
                className="w-full font-mono rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isProcessing}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-500 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-500/20 hover:bg-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                {isProcessing ? (
                  <>
                    <span className="animate-spin h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full" />
                    <span>Processing Simulated Webhook...</span>
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-5 h-5" />
                    <span>SIMULATE GITHUB PUSH EVENT</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Output & Pipeline Timeline Column */}
        <div className="space-y-6">
          {/* Simulated Pipeline Execution Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-4 pb-2 border-b border-slate-800/80 flex items-center justify-between">
              <span>Simulated Pipeline Timeline</span>
              {isProcessing && <span className="text-xs text-emerald-400 animate-pulse">Running stages...</span>}
            </h3>

            <div className="space-y-3">
              {[
                { title: '1. Webhook Dispatch', desc: 'POST payload delivered with X-GitHub-Delivery' },
                { title: '2. HMAC Signature Verification', desc: 'Validates SHA256 digest via Secrets Manager token' },
                { title: '3. Branch & Deletion Filtering', desc: 'Checks branch against target monitored branch' },
                { title: '4. Metadata & Schema v1 Extraction', desc: 'Constructs canonical GitOps payload' },
                { title: '5. MQTT Publication (Simulated)', desc: 'Broadcast to topic gitops/commits (QoS 0)' }
              ].map((step, idx) => {
                const stepNum = idx + 1;
                const isDone = lastResult ? true : activeStep >= stepNum;
                const isCurrent = activeStep === stepNum && isProcessing;

                return (
                  <div
                    key={step.title}
                    className={`flex items-start gap-3 rounded-lg p-3 transition-colors ${
                      isCurrent
                        ? 'bg-emerald-500/10 border border-emerald-500/30'
                        : isDone
                        ? 'bg-slate-900/80 border border-slate-800'
                        : 'opacity-40 bg-slate-950/40 border border-slate-900'
                    }`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : isCurrent ? (
                        <div className="w-4 h-4 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-700 text-[10px] flex items-center justify-center text-slate-500 font-mono">
                          {stepNum}
                        </div>
                      )}
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-200">{step.title}</h4>
                      <p className="text-[11px] text-slate-400">{step.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Result Card */}
          {lastResult && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Simulation Output
                </span>
                <button
                  type="button"
                  onClick={() => onSelectEvent(lastResult)}
                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                >
                  <span>Open Full Event Details</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Status Message Banner */}
              <div
                className={`rounded-lg p-3 text-xs leading-relaxed border ${
                  lastResult.status === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : lastResult.status === 'ignored'
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                }`}
              >
                <div className="font-bold flex items-center gap-1.5 mb-1">
                  {lastResult.status === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : lastResult.status === 'ignored' ? (
                    <Radio className="w-4 h-4 text-amber-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                  )}
                  <span>Status: {lastResult.status.toUpperCase()}</span>
                </div>
                <p>{lastResult.statusReason}</p>
              </div>

              {/* Generated Schema v1 MQTT Preview */}
              {lastResult.mqttPayload ? (
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">
                      Generated MQTT Message Payload:
                    </span>
                    <span className="text-[11px] font-mono text-emerald-400">Topic: gitops/commits (QoS 0)</span>
                  </div>
                  <JsonViewer data={lastResult.mqttPayload} title="MQTT Schema v1 Payload" maxHeight="max-h-56" />
                </div>
              ) : (
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-center text-xs text-slate-500">
                  No MQTT message was published for this simulated event because it was filtered/ignored by the Lambda processor.
                </div>
              )}

              {triggerSelect && (
                <div className="pt-2 text-right">
                  <button
                    onClick={() => triggerSelect(lastResult)}
                    type="button"
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    <span>Inspect Full Event Metadata & Raw Payload &rarr;</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PushSimulatorSection;
