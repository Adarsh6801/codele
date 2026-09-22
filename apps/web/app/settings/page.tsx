'use client';

import { ChangeEvent, useEffect, useState } from 'react';
import { ImageCropper } from '../components/image-cropper';
import { AppShell } from '../components/app-shell';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const origin = api.replace('/api/v1', '');
type Profile = {
  display_name: string;
  email: string;
  level: string;
  profile_image_url: string | null;
  cover_image_url: string | null;
  linkedin_url: string | null;
  leaderboard_visible: boolean;
  display_name_changes_remaining: number;
  display_name_change_available_at: string | null;
};
type CropTarget = { file: File; kind: 'avatar' | 'cover' };
type Badge = { code: string; name: string; description: string; icon: string; awarded_at: string };
type NotificationPreferences = {
  in_app_enabled: boolean;
  submission_updates: boolean;
  achievement_updates: boolean;
  social_updates: boolean;
  account_updates: boolean;
};

export default function Settings() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [leaderboardVisible, setLeaderboardVisible] = useState(true);
  const [cropTarget, setCropTarget] = useState<CropTarget | null>(null);
  const [avatarData, setAvatarData] = useState<string | null>(null);
  const [coverData, setCoverData] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState('');
  const [badges, setBadges] = useState<Badge[]>([]);
  const [notificationPreferences, setNotificationPreferences] =
    useState<NotificationPreferences | null>(null);
  const headers = () => ({
    Authorization: `Bearer ${localStorage.getItem('codele_token')}`,
    'Content-Type': 'application/json',
  });
  const load = async () => {
    const response = await fetch(`${api}/auth/me`, { headers: headers() });
    if (!response.ok) throw new Error('Could not load your profile.');
    const data = (await response.json()) as Profile;
    setProfile(data);
    setDisplayName(data.display_name);
    setLinkedinUrl(data.linkedin_url ?? '');
    setLeaderboardVisible(data.leaderboard_visible);
  };
  useEffect(() => {
    load().catch((error) => setError(error.message));
    fetch(`${api}/progress`, { headers: headers() })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setBadges(data?.badges ?? []));
    fetch(`${api}/notifications/preferences`, { headers: headers() })
      .then((response) =>
        response.ok
          ? response.json()
          : Promise.reject(new Error('Could not load notification preferences.')),
      )
      .then(setNotificationPreferences)
      .catch((reason) => setError(reason.message));
  }, []);
  const saveNotificationPreferences = async (next: NotificationPreferences) => {
    setSaving('notifications');
    setError('');
    setNotice('');
    try {
      const response = await fetch(`${api}/notifications/preferences`, {
        method: 'PUT',
        headers: headers(),
        body: JSON.stringify(next),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok)
        throw new Error(
          typeof body.detail === 'string'
            ? body.detail
            : 'Unable to save notification preferences.',
        );
      setNotificationPreferences(body as NotificationPreferences);
      setNotice('Notification preferences updated.');
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving('');
    }
  };
  const update = async (response: Response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok)
      throw new Error(
        typeof body.detail === 'string' ? body.detail : 'Unable to save your profile.',
      );
    const data = body as Profile;
    setProfile(data);
    setDisplayName(data.display_name);
    setLinkedinUrl(data.linkedin_url ?? '');
    setLeaderboardVisible(data.leaderboard_visible);
    window.dispatchEvent(new Event('codele-profile-updated'));
  };
  const saveDetails = async () => {
    if (!/^[A-Za-z0-9_-]{3,80}$/.test(displayName.trim()))
      return setError('Use 3–80 letters, numbers, _ or - for your display name.');
    setSaving('details');
    setError('');
    setNotice('');
    try {
      await update(
        await fetch(`${api}/auth/me`, {
          method: 'PATCH',
          headers: headers(),
          body: JSON.stringify({
            display_name: displayName.trim(),
            linkedin_url: linkedinUrl,
            leaderboard_visible: leaderboardVisible,
          }),
        }),
      );
      setNotice('Profile details updated.');
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving('');
    }
  };
  const choose = (kind: CropTarget['kind']) => (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (
      !['image/png', 'image/jpeg', 'image/webp'].includes(file.type) ||
      file.size > 5 * 1024 * 1024
    )
      return setError('Choose a PNG, JPEG, or WebP image no larger than 5 MB.');
    setCropTarget({ file, kind });
    event.target.value = '';
  };
  const saveAsset = async (kind: CropTarget['kind'], dataUrl: string) => {
    setSaving(kind);
    setError('');
    setNotice('');
    try {
      await update(
        await fetch(`${api}/auth/me/${kind === 'avatar' ? 'profile-image' : 'cover-image'}`, {
          method: 'PUT',
          headers: headers(),
          body: JSON.stringify({ image_data_url: dataUrl }),
        }),
      );
      if (kind === 'avatar') setAvatarData(null);
      else setCoverData(null);
      setNotice(`${kind === 'avatar' ? 'Profile photo' : 'Cover banner'} updated.`);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving('');
    }
  };
  const cropReady = (dataUrl: string) => {
    if (!cropTarget) return;
    if (cropTarget.kind === 'avatar') setAvatarData(dataUrl);
    else setCoverData(dataUrl);
    setCropTarget(null);
  };
  const avatar =
    avatarData ?? (profile?.profile_image_url ? `${origin}${profile.profile_image_url}` : null);
  const cover =
    coverData ?? (profile?.cover_image_url ? `${origin}${profile.cover_image_url}` : null);
  const locked = profile?.display_name_changes_remaining === 0;
  return (
    <AppShell>
      <main className="profile-page">
        <section
          className="profile-cover"
          style={cover ? { backgroundImage: `url(${cover})` } : undefined}
        >
          <div>&lt;/&gt; 0101 {'{}'} &lt;/&gt;</div>
          <label className="cover-picker">
            Edit cover
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={choose('cover')}
            />
          </label>
          {coverData && (
            <button
              className="button cover-save"
              onClick={() => saveAsset('cover', coverData)}
              disabled={saving === 'cover'}
            >
              {saving === 'cover' ? 'Saving…' : 'Save cover'}
            </button>
          )}
        </section>
        <section className="profile-header">
          <div className="profile-photo">
            {avatar ? (
              <img src={avatar} alt="Your profile" />
            ) : (
              <span>{profile?.display_name?.slice(0, 1).toUpperCase() ?? '…'}</span>
            )}
            <label className="photo-picker">
              ⌁
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={choose('avatar')}
              />
            </label>
          </div>
          <div>
            <p className="eyebrow">{profile?.level ?? 'ROOKIE'} CODER</p>
            <h1>{profile?.display_name ?? 'Your profile'}</h1>
            <p>{profile?.email}</p>
          </div>
          {avatarData && (
            <button
              className="button save-photo"
              onClick={() => saveAsset('avatar', avatarData)}
              disabled={saving === 'avatar'}
            >
              {saving === 'avatar' ? 'Saving…' : 'Save photo'}
            </button>
          )}
        </section>
        <section className="profile-grid">
          <article className="profile-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">IDENTITY</p>
                <h2>Personal details</h2>
              </div>
              <span className="card-icon">✎</span>
            </div>
            <label>
              Display name
              <input
                value={displayName}
                disabled={locked}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </label>
            <label className="privacy-toggle">
              <input
                type="checkbox"
                checked={leaderboardVisible}
                onChange={(event) => setLeaderboardVisible(event.target.checked)}
              />
              <span>
                <b>Appear on leaderboards</b>
                <small>Friends and other learners can see your display name, XP, and streak.</small>
              </span>
            </label>
            <div className="change-limit">
              <span>{profile?.display_name_changes_remaining ?? 3} / 3 changes available</span>
              <p>
                {locked
                  ? `Display-name changes unlock ${new Date(profile?.display_name_change_available_at ?? '').toLocaleString()}.`
                  : 'Three display-name changes are allowed every 24 hours.'}
              </p>
            </div>
            <label>
              LinkedIn profile URL
              <input
                placeholder="https://www.linkedin.com/in/your-name"
                value={linkedinUrl}
                onChange={(event) => setLinkedinUrl(event.target.value)}
              />
            </label>
            <button
              className="button profile-save"
              onClick={saveDetails}
              disabled={saving === 'details'}
            >
              {saving === 'details' ? 'Saving…' : 'Save profile'}
            </button>
          </article>
          <aside className="profile-card photo-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">PROFILE MEDIA</p>
                <h2>Make it yours</h2>
              </div>
              <span className="card-icon">◉</span>
            </div>
            <p>
              Crop a square avatar and a wide cover banner before saving. Previous images are
              automatically removed from storage.
            </p>
            <label className="photo-button">
              Choose profile photo
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={choose('avatar')}
              />
            </label>
          </aside>
        </section>
        <section className="profile-card badge-showcase">
          <div className="card-heading">
            <div>
              <p className="eyebrow">GAMIFICATION</p>
              <h2>Badge showcase</h2>
            </div>
            <span className="card-icon">✦</span>
          </div>
          {badges.length ? (
            <div className="badge-list">
              {badges.map((badge) => (
                <article key={badge.code}>
                  <span>{badge.icon}</span>
                  <div>
                    <b>{badge.name}</b>
                    <p>{badge.description}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p>
              Complete your first daily challenge to earn your first badge. Each award is recorded
              once on your profile.
            </p>
          )}
        </section>
        <section className="profile-card notification-preferences-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">PREFERENCES</p>
              <h2>Notifications</h2>
            </div>
            <span className="card-icon">♢</span>
          </div>
          {notificationPreferences ? (
            <fieldset className="notification-settings" disabled={saving === 'notifications'}>
              <legend>Choose the activity that appears in your notification center.</legend>
              {(
                [
                  [
                    'in_app_enabled',
                    'In-app notifications',
                    'Pause or resume all alerts in your Codele notification center.',
                  ],
                  [
                    'submission_updates',
                    'Submission results',
                    'Know when a secure code evaluation has finished.',
                  ],
                  [
                    'achievement_updates',
                    'Achievements',
                    'Receive alerts for new badges and streak milestones.',
                  ],
                  [
                    'social_updates',
                    'Social activity',
                    'Receive friend-request and acceptance alerts.',
                  ],
                  [
                    'account_updates',
                    'Account updates',
                    'Receive important account and security updates.',
                  ],
                ] as const
              ).map(([key, label, description]) => (
                <label className="privacy-toggle" key={key}>
                  <input
                    type="checkbox"
                    checked={notificationPreferences[key]}
                    onChange={(event) =>
                      void saveNotificationPreferences({
                        ...notificationPreferences,
                        [key]: event.target.checked,
                      })
                    }
                  />
                  <span>
                    <b>{label}</b>
                    <small>{description}</small>
                  </span>
                </label>
              ))}
            </fieldset>
          ) : (
            <p>Loading notification preferences…</p>
          )}
        </section>
        {notice && <p className="profile-notice">✓ {notice}</p>}
        {error && <p className="profile-error">{error}</p>}
        {cropTarget && (
          <ImageCropper
            file={cropTarget.file}
            aspect={cropTarget.kind === 'avatar' ? 1 : 2.8}
            title={cropTarget.kind === 'avatar' ? 'Crop profile photo' : 'Crop cover banner'}
            onCancel={() => setCropTarget(null)}
            onConfirm={cropReady}
          />
        )}
      </main>
    </AppShell>
  );
}
