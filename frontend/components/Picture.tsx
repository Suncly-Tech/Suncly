/**
 * One of the six pictures from frontend/art, rendered by scripts/render-art.mjs to
 * public/art/<name>-{640,1280,1920}.{avif,webp}. Art-directed crop per breakpoint through
 * object-fit and an aspect ratio; explicit dimensions; lazy below the fold; the hero
 * image is preloaded and eager.
 */

export type ArtName = "two-cards" | "aperture" | "analemma" | "specimens" | "seal" | "last-light";

const DIMENSIONS: Record<ArtName, { width: number; height: number }> = {
  "two-cards": { width: 1300, height: 920 },
  aperture: { width: 1500, height: 1125 },
  analemma: { width: 1500, height: 1125 },
  specimens: { width: 1800, height: 800 },
  seal: { width: 1000, height: 1000 },
  "last-light": { width: 1800, height: 560 },
};

export function Picture({
  name,
  alt,
  sizes,
  priority = false,
  className = "",
  imgClassName = "",
}: {
  name: ArtName;
  /** Real alt text, or an empty string when the picture is decorative. */
  alt: string;
  /** The `sizes` attribute, matching the layout. */
  sizes: string;
  priority?: boolean;
  className?: string;
  imgClassName?: string;
}) {
  const { width, height } = DIMENSIONS[name];
  const srcset = (ext: "avif" | "webp") => [640, 1280, 1920].map((w) => `/art/${name}-${w}.${ext} ${w}w`).join(", ");
  return (
    <picture className={`picture-plate ${className}`}>
      <source type="image/avif" srcSet={srcset("avif")} sizes={sizes} />
      <source type="image/webp" srcSet={srcset("webp")} sizes={sizes} />
      <img
        src={`/art/${name}-1280.webp`}
        srcSet={srcset("webp")}
        sizes={sizes}
        width={width}
        height={height}
        alt={alt}
        loading={priority ? "eager" : "lazy"}
        decoding={priority ? "sync" : "async"}
        fetchPriority={priority ? "high" : "auto"}
        className={imgClassName}
      />
    </picture>
  );
}
