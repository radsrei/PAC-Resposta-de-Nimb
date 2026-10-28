import React, { useEffect, useRef } from 'react';

// Explosão de confetes saindo dos 4 cantos da tela em direção ao centro.
// Canvas sem dependências; some sozinho após DURATION_MS e não bloqueia cliques.

const DURATION_MS = 1300;
const PER_CORNER = 45;
const COLORS = ['#FF8A00', '#FFB547', '#A259FF', '#d8b9ff', '#39D98A', '#F0EEF8'];

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  rotation: number;
  spin: number;
}

interface ConfettiBurstProps {
  /** Muda a cada explosão; 0 = nenhuma. */
  burstKey: number;
}

export const ConfettiBurst: React.FC<ConfettiBurstProps> = ({ burstKey }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!burstKey || !canvas || !ctx) return;

    const width = (canvas.width = window.innerWidth);
    const height = (canvas.height = window.innerHeight);
    const speed = Math.max(width, height) / 55;

    const corners = [
      [0, 0],
      [width, 0],
      [0, height],
      [width, height],
    ];
    const particles: Particle[] = corners.flatMap(([cx, cy]) => {
      const toCenter = Math.atan2(height / 2 - cy, width / 2 - cx);
      return Array.from({ length: PER_CORNER }, () => {
        const angle = toCenter + (Math.random() - 0.5) * 1.1;
        const v = speed * (0.45 + Math.random() * 0.75);
        return {
          x: cx,
          y: cy,
          vx: Math.cos(angle) * v,
          vy: Math.sin(angle) * v,
          size: 5 + Math.random() * 6,
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
          rotation: Math.random() * Math.PI,
          spin: (Math.random() - 0.5) * 0.4,
        };
      });
    });

    const started = performance.now();
    let frame = 0;

    const draw = (now: number) => {
      const progress = (now - started) / DURATION_MS;
      ctx.clearRect(0, 0, width, height);
      if (progress >= 1) return;

      ctx.globalAlpha = 1 - progress * progress;
      for (const p of particles) {
        p.vx *= 0.96;
        p.vy = p.vy * 0.96 + 0.35; // atrito + gravidade
        p.x += p.vx;
        p.y += p.vy;
        p.rotation += p.spin;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
        ctx.restore();
      }
      frame = requestAnimationFrame(draw);
    };

    frame = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(frame);
      ctx.clearRect(0, 0, width, height);
    };
  }, [burstKey]);

  return <canvas ref={canvasRef} className="fixed inset-0 z-[100] pointer-events-none" aria-hidden="true" />;
};
