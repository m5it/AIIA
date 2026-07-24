// TUNED GitHub Profile Extractor for LLM Consumption
// Returns structured JSON instead of raw HTML

(function() {
  const result = {
    profile: {},
    repositories: [],
    activity: [],
    extracted_at: new Date().toISOString()
  };
  
  // Profile Header
  const nameEl = document.querySelector('.vcard-fullname, [itemprop="name"]');
  const bioEl = document.querySelector('.user-profile-bio, [itemprop="description"]');
  const avatarEl = document.querySelector('.avatar-user');
  
  result.profile = {
    name: nameEl?.textContent?.trim() || document.querySelector('h1')?.textContent?.trim(),
    username: document.querySelector('.vcard-username')?.textContent?.trim() || 
              window.location.pathname.split('/')[1],
    bio: bioEl?.textContent?.trim(),
    avatar_url: avatarEl?.src,
    location: document.querySelector('[itemprop="homeLocation"]')?.textContent?.trim(),
    company: document.querySelector('[itemprop="worksFor"]')?.textContent?.trim(),
    website: document.querySelector('[itemprop="url"]')?.href,
    followers: document.querySelector('a[href$="?tab=followers"] .text-bold')?.textContent?.trim(),
    following: document.querySelector('a[href$="?tab=following"] .text-bold')?.textContent?.trim()
  };
  
  // Repository Cards - with defensive extraction
  const repoCards = document.querySelectorAll('[data-testid="repo-list-item"], .repo-list-item, article.Box');
  repoCards.forEach(card => {
    const repo = {
      name: card.querySelector('h3 a, .repo-list-name a')?.textContent?.trim(),
      description: card.querySelector('p, .repo-list-description')?.textContent?.trim(),
      language: card.querySelector('[itemprop="programmingLanguage"]')?.textContent?.trim(),
      stars: card.querySelector('[href$="/stargazers"]')?.textContent?.trim(),
      forks: card.querySelector('[href$="/network/members"]')?.textContent?.trim(),
      updated: card.querySelector('relative-time')?.textContent?.trim()
    };
    if (repo.name) result.repositories.push(repo);
  });
  
  // Alternative: List view repos
  if (result.repositories.length === 0) {
    document.querySelectorAll('#user-repositories-list li, .repo-list li').forEach(li => {
      const repo = {
        name: li.querySelector('h3 a')?.textContent?.trim(),
        description: li.querySelector('p')?.textContent?.trim(),
        language: li.querySelector('[itemprop="programmingLanguage"]')?.textContent?.trim(),
        stars: li.querySelector('.stars')?.textContent?.trim(),
        updated: li.querySelector('relative-time')?.textContent?.trim()
      };
      if (repo.name) result.repositories.push(repo);
    });
  }
  
  // Recent Activity (if available)
  document.querySelectorAll('.contribution-activity-listing, .TimelineItem').forEach(item => {
    const activity = {
      type: item.querySelector('.contribution-activity')?.textContent?.trim() || 'commit',
      description: item.textContent?.trim().substring(0, 200),
      date: item.querySelector('time, relative-time')?.textContent?.trim()
    };
    result.activity.push(activity);
  });
  
  // Return clean JSON for LLM consumption
  return JSON.stringify(result, null, 2);
})();