<script setup lang="ts">
import VaultHudPanel from '../vault/VaultHudPanel.vue';
import { useSkillsSurface } from '../../composables/useSkillsSurface';

const { loading, error, groups, summary, refresh } = useSkillsSurface();
</script>

<template>
  <main class="region region-center-workbench skills-surface" aria-label="Operator skills">
    <VaultHudPanel tag="div" panel-class="skills-surface__shell">
      <header class="skills-surface__hero">
        <div class="skills-surface__hero-copy">
          <p class="skills-surface__eyebrow">Operator foundation</p>
          <div class="skills-surface__title-row">
            <h1 class="skills-surface__title">Skills</h1>
          </div>
          <p class="skills-surface__subtitle">
            Agent playbooks discovered from bound workspace
            <code>.github/skills/*/SKILL.md</code> files.
          </p>
          <p class="skills-surface__summary">{{ summary }}</p>
        </div>
        <div class="skills-surface__hero-actions">
          <button type="button" class="skills-surface__button" :disabled="loading" @click="refresh">
            {{ loading ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>
      </header>

      <p v-if="error" class="skills-surface__error" role="alert">{{ error }}</p>
      <p v-else-if="loading && !groups.length" class="skills-surface__loading">
        Loading skills…
      </p>

      <div v-else class="skills-surface__body">
        <VaultHudPanel
          v-for="group in groups"
          :key="group.workspaceId"
          panel-class="skills-surface__panel"
        >
          <div class="skills-surface__panel-head">
            <h2 class="skills-surface__panel-title">{{ group.workspaceLabel }}</h2>
            <p class="skills-surface__panel-meta">
              {{ group.skills.length }} skill(s) · {{ group.workspaceId }}
            </p>
          </div>
          <ul class="skills-surface__list">
            <li v-for="skill in group.skills" :key="skill.id" class="skills-surface__item">
              <div class="skills-surface__item-head">
                <strong class="skills-surface__item-name">{{ skill.name }}</strong>
                <code class="skills-surface__item-path">{{ skill.path }}</code>
              </div>
              <p v-if="skill.description" class="skills-surface__item-desc">
                {{ skill.description }}
              </p>
            </li>
          </ul>
        </VaultHudPanel>
      </div>
    </VaultHudPanel>
  </main>
</template>
