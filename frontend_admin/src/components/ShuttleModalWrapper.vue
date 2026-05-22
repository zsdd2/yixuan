<template>
  <teleport to="body">
    <transition name="modal-fade">
      <div v-if="visible" class="shuttle-mask" @click.self="$emit('close')">
        <div class="shuttle-container">
          <!-- 穿梭台组件插入点 -->
          <slot />
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
defineProps<{ visible: boolean }>()
defineEmits<{ close: [] }>()
</script>

<style scoped>
.shuttle-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.shuttle-container {
  width: 90vw;
  height: 90vh;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.25);
}

.w-5 { width: 20px; height: 20px; }

/* Transition */
.modal-fade-enter-active { transition: all 0.25s ease-out; }
.modal-fade-leave-active { transition: all 0.2s ease-in; }
.modal-fade-enter-from { opacity: 0; }
.modal-fade-enter-from .shuttle-container { transform: scale(0.95) translateY(20px); }
.modal-fade-leave-to { opacity: 0; }
.modal-fade-leave-to .shuttle-container { transform: scale(0.95); }
</style>
