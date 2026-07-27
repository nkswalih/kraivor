'use client';

import { useRef, useEffect, useCallback } from 'react';

interface CanvasGridProps {
  viewport: { x: number; y: number; zoom: number };
  gridSize: number;
  enabled: boolean;
}

const GLOW_RADIUS = 200;
const BASE_DOT_RADIUS = 1;
const GLOW_DOT_RADIUS = 1.3;
const BASE_ALPHA = 0.16;
const GLOW_ALPHA = 0.28;

export function CanvasGrid({ viewport, gridSize, enabled }: CanvasGridProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef<{ x: number; y: number } | null>(null);
  const rafRef = useRef(0);
  const dotColorRef = useRef('#2c2c33');
  const glowColorRef = useRef('#e8c547');

  useEffect(() => {
    const cs = getComputedStyle(document.documentElement);
    const border = cs.getPropertyValue('--krait-border').trim();
    const venom = cs.getPropertyValue('--venom-yellow').trim();
    if (border) dotColorRef.current = border;
    if (venom) glowColorRef.current = venom;
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const parent = canvas.parentElement;
    if (!parent) return;

    const rect = parent.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = rect.width;
    const h = rect.height;

    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const spacing = Math.max(14, Math.min(48, gridSize * viewport.zoom));
    if (spacing < 4) return;

    const offsetX = viewport.x % spacing;
    const offsetY = viewport.y % spacing;

    const dotColor = dotColorRef.current;
    const mouse = mouseRef.current;

    let glowWorldX: number | null = null;
    let glowWorldY: number | null = null;
    if (mouse) {
      glowWorldX = (mouse.x - viewport.x) / viewport.zoom;
      glowWorldY = (mouse.y - viewport.y) / viewport.zoom;
    }

    const startX = offsetX - spacing;
    const startY = offsetY - spacing;
    const cols = Math.ceil(w / spacing) + 3;
    const rows = Math.ceil(h / spacing) + 3;

    const glowRadiusWorld = GLOW_RADIUS / viewport.zoom;
    const glowRadiusWorldSq = glowRadiusWorld * glowRadiusWorld;

    const venomR = parseInt(glowColorRef.current.slice(1, 3), 16);
    const venomG = parseInt(glowColorRef.current.slice(3, 5), 16);
    const venomB = parseInt(glowColorRef.current.slice(5, 7), 16);

    const baseR = parseInt(dotColor.slice(1, 3), 16);
    const baseG = parseInt(dotColor.slice(3, 5), 16);
    const baseB = parseInt(dotColor.slice(5, 7), 16);

    for (let row = 0; row < rows; row++) {
      const dotScreenY = startY + row * spacing;
      const worldY = (dotScreenY - viewport.y) / viewport.zoom;

      for (let col = 0; col < cols; col++) {
        const dotScreenX = startX + col * spacing;

        let alpha = BASE_ALPHA;
        let radius = BASE_DOT_RADIUS;
        let r = baseR;
        let g = baseG;
        let b = baseB;

        if (glowWorldX !== null && glowWorldY !== null) {
          const dx = (dotScreenX - viewport.x) / viewport.zoom - glowWorldX;
          const dy = worldY - glowWorldY;
          const distSq = dx * dx + dy * dy;

          if (distSq < glowRadiusWorldSq) {
            const dist = Math.sqrt(distSq);
            const t = 1 - dist / glowRadiusWorld;
            const ease = t * t * t * t;
            alpha = BASE_ALPHA + (GLOW_ALPHA - BASE_ALPHA) * ease;
            radius = BASE_DOT_RADIUS + (GLOW_DOT_RADIUS - BASE_DOT_RADIUS) * ease;
            r = Math.round(baseR + (venomR - baseR) * ease);
            g = Math.round(baseG + (venomG - baseG) * ease);
            b = Math.round(baseB + (venomB - baseB) * ease);
          }
        }

        ctx.globalAlpha = alpha;
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.beginPath();
        ctx.arc(dotScreenX, dotScreenY, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    if (mouse && glowWorldX !== null) {
      const gradient = ctx.createRadialGradient(
        mouse.x, mouse.y, 0,
        mouse.x, mouse.y, GLOW_RADIUS
      );
      gradient.addColorStop(0, 'rgba(232, 197, 71, 0.008)');
      gradient.addColorStop(0.5, 'rgba(232, 197, 71, 0.003)');
      gradient.addColorStop(1, 'rgba(232, 197, 71, 0)');
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'screen';
      ctx.fillStyle = gradient;
      ctx.fillRect(mouse.x - GLOW_RADIUS, mouse.y - GLOW_RADIUS, GLOW_RADIUS * 2, GLOW_RADIUS * 2);
      ctx.globalCompositeOperation = 'source-over';
    }
  }, [viewport, gridSize]);

  useEffect(() => {
    if (!enabled) {
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    let running = true;

    const loop = () => {
      if (!running) return;
      draw();
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);

    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [enabled, draw]);

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (!rect) return;
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    };

    const handleLeave = () => {
      mouseRef.current = null;
    };

    window.addEventListener('mousemove', handleMove, { passive: true });
    window.addEventListener('mouseleave', handleLeave);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseleave', handleLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
}
