import { useState } from 'react';
import { Lock } from 'lucide-react';
import { toast } from 'sonner';
import { SectionCard } from '@/components/app/PageLayout';
import { SaveBar } from '@/components/app/SaveBar';
import { Badge } from '@/components/ui/badge';
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldLabel,
  FieldTitle,
} from '@/components/ui/field';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { saveJobMatchPreferences, saveJobShareDefaultSettings } from '@/api/settingsApi';
import { JOB_SHARE_DEFAULT_OPTIONS } from '@/features/jobs/jobAddShare';
import type { JobShareDefault, UserSettings } from '@/types/settings';
import { extractApiErrorMessage } from '@/utils/profileErrors';
import { useSetSettings } from './queries';
import { useDraft, useReportDirty } from './useDraft';

export function JobSearchTab({
  settings,
  active,
  onDirtyChange,
}: {
  settings: UserSettings;
  active: boolean;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const setSettings = useSetSettings();
  const [savingShare, setSavingShare] = useState(false);
  const saved = { preferences: settings.job_match_preferences ?? '' };
  const { values, set, clear } = useDraft(saved);
  const [saving, setSaving] = useState(false);

  const maxLength = settings.job_match_preferences_max_length || 4000;
  const prefsLength = values.preferences.trim().length;
  const prefsTooLong = prefsLength > maxLength;
  const dirty = values.preferences.trim() !== saved.preferences.trim();
  useReportDirty(dirty, onDirtyChange);

  const handleSave = async () => {
    setSaving(true);
    try {
      const trimmed = values.preferences.trim();
      setSettings(
        await saveJobMatchPreferences(
          trimmed ? { job_match_preferences: trimmed } : { clear_job_match_preferences: true },
        ),
      );
      clear(['preferences']);
      toast.success('Job search preferences saved', {
        description: trimmed
          ? 'Re-run match analysis on existing jobs to apply your preferences.'
          : 'Job match preferences cleared.',
      });
    } catch (err) {
      toast.error(extractApiErrorMessage(err, 'Failed to save job search preferences.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title="When you add jobs"
        description={
          settings.job_share_locked
            ? `Set by your team lead (${settings.team_space_name ?? 'your team'}). Jobs you add are always stored with this sharing.`
            : 'Every job you add is stored with this sharing. You can change it later for a single add from the sidebar history.'
        }
        actions={
          settings.job_share_locked ? (
            <Badge variant="secondary" className="gap-1">
              <Lock className="size-3" aria-hidden />
              Set by your team lead
            </Badge>
          ) : null
        }
      >
        <RadioGroup
          aria-label="Default sharing for jobs you add"
          value={settings.job_share_default}
          disabled={savingShare || settings.job_share_locked}
          onValueChange={(value) => {
            const next = value as JobShareDefault;
            if (next === settings.job_share_default) return;
            setSavingShare(true);
            void saveJobShareDefaultSettings({ job_share_default: next })
              .then((updated) => {
                setSettings(updated);
                toast.success('Default sharing saved');
              })
              .catch((err) => {
                toast.error(extractApiErrorMessage(err, 'Failed to save default sharing.'));
              })
              .finally(() => setSavingShare(false));
          }}
        >
          {JOB_SHARE_DEFAULT_OPTIONS.map((opt) => (
            <FieldLabel key={opt.value} htmlFor={`job-share-${opt.value}`}>
              <Field orientation="horizontal">
                <RadioGroupItem
                  value={opt.value}
                  id={`job-share-${opt.value}`}
                  aria-labelledby={`job-share-${opt.value}-title`}
                  aria-describedby={`job-share-${opt.value}-hint`}
                />
                <FieldContent>
                  <FieldTitle id={`job-share-${opt.value}-title`}>{opt.label}</FieldTitle>
                  <FieldDescription id={`job-share-${opt.value}-hint`}>{opt.hint}</FieldDescription>
                </FieldContent>
              </Field>
            </FieldLabel>
          ))}
        </RadioGroup>
      </SectionCard>

      <SectionCard
        title="Job match preferences"
        description="Tell the AI what roles you want. The match analysis uses this when scoring jobs."
      >
        <Field data-invalid={prefsTooLong || undefined}>
          <div className="flex items-baseline justify-between gap-2">
            <FieldLabel htmlFor="job-match-preferences">What you're looking for</FieldLabel>
            <span className={cn('text-xs tabular-nums text-muted-foreground', prefsTooLong && 'text-destructive')}>
              {prefsLength.toLocaleString()} / {maxLength.toLocaleString()}
            </span>
          </div>
          <Textarea
            id="job-match-preferences"
            value={values.preferences}
            maxLength={maxLength}
            disabled={saving}
            aria-invalid={prefsTooLong || undefined}
            onChange={(e) => set({ preferences: e.target.value })}
            rows={7}
            className="min-h-40"
            placeholder={
              'e.g.\n- Senior backend / platform engineer roles\n- Prefer fintech, developer tools, or infra startups\n- Target compensation $160k+\n- Avoid roles requiring security clearance'
            }
          />
          <FieldDescription>
            Titles, industries, salary, company size, tech stack, or roles to avoid. Filter remote, hybrid, or onsite
            from the Jobs table Work mode control. Re-run analysis to apply changes to existing jobs.
          </FieldDescription>
          {prefsTooLong ? <FieldError>Keep it under {maxLength.toLocaleString()} characters.</FieldError> : null}
        </Field>
      </SectionCard>

      <SaveBar
        dirty={dirty && active}
        saving={saving}
        disabled={prefsTooLong}
        onSave={() => void handleSave()}
        onDiscard={() => clear()}
      />
    </div>
  );
}
