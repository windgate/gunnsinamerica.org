declare module 'astro:content' {
	interface RenderResult {
		Content: import('astro/runtime/server/index.js').AstroComponentFactory;
		headings: import('astro').MarkdownHeading[];
		remarkPluginFrontmatter: Record<string, any>;
	}
	interface Render {
		'.md': Promise<RenderResult>;
	}

	export interface RenderedContent {
		html: string;
		metadata?: {
			imagePaths: Array<string>;
			[key: string]: unknown;
		};
	}
}

declare module 'astro:content' {
	type Flatten<T> = T extends { [K: string]: infer U } ? U : never;

	export type CollectionKey = keyof AnyEntryMap;
	export type CollectionEntry<C extends CollectionKey> = Flatten<AnyEntryMap[C]>;

	export type ContentCollectionKey = keyof ContentEntryMap;
	export type DataCollectionKey = keyof DataEntryMap;

	type AllValuesOf<T> = T extends any ? T[keyof T] : never;
	type ValidContentEntrySlug<C extends keyof ContentEntryMap> = AllValuesOf<
		ContentEntryMap[C]
	>['slug'];

	/** @deprecated Use `getEntry` instead. */
	export function getEntryBySlug<
		C extends keyof ContentEntryMap,
		E extends ValidContentEntrySlug<C> | (string & {}),
	>(
		collection: C,
		// Note that this has to accept a regular string too, for SSR
		entrySlug: E,
	): E extends ValidContentEntrySlug<C>
		? Promise<CollectionEntry<C>>
		: Promise<CollectionEntry<C> | undefined>;

	/** @deprecated Use `getEntry` instead. */
	export function getDataEntryById<C extends keyof DataEntryMap, E extends keyof DataEntryMap[C]>(
		collection: C,
		entryId: E,
	): Promise<CollectionEntry<C>>;

	export function getCollection<C extends keyof AnyEntryMap, E extends CollectionEntry<C>>(
		collection: C,
		filter?: (entry: CollectionEntry<C>) => entry is E,
	): Promise<E[]>;
	export function getCollection<C extends keyof AnyEntryMap>(
		collection: C,
		filter?: (entry: CollectionEntry<C>) => unknown,
	): Promise<CollectionEntry<C>[]>;

	export function getEntry<
		C extends keyof ContentEntryMap,
		E extends ValidContentEntrySlug<C> | (string & {}),
	>(entry: {
		collection: C;
		slug: E;
	}): E extends ValidContentEntrySlug<C>
		? Promise<CollectionEntry<C>>
		: Promise<CollectionEntry<C> | undefined>;
	export function getEntry<
		C extends keyof DataEntryMap,
		E extends keyof DataEntryMap[C] | (string & {}),
	>(entry: {
		collection: C;
		id: E;
	}): E extends keyof DataEntryMap[C]
		? Promise<DataEntryMap[C][E]>
		: Promise<CollectionEntry<C> | undefined>;
	export function getEntry<
		C extends keyof ContentEntryMap,
		E extends ValidContentEntrySlug<C> | (string & {}),
	>(
		collection: C,
		slug: E,
	): E extends ValidContentEntrySlug<C>
		? Promise<CollectionEntry<C>>
		: Promise<CollectionEntry<C> | undefined>;
	export function getEntry<
		C extends keyof DataEntryMap,
		E extends keyof DataEntryMap[C] | (string & {}),
	>(
		collection: C,
		id: E,
	): E extends keyof DataEntryMap[C]
		? Promise<DataEntryMap[C][E]>
		: Promise<CollectionEntry<C> | undefined>;

	/** Resolve an array of entry references from the same collection */
	export function getEntries<C extends keyof ContentEntryMap>(
		entries: {
			collection: C;
			slug: ValidContentEntrySlug<C>;
		}[],
	): Promise<CollectionEntry<C>[]>;
	export function getEntries<C extends keyof DataEntryMap>(
		entries: {
			collection: C;
			id: keyof DataEntryMap[C];
		}[],
	): Promise<CollectionEntry<C>[]>;

	export function render<C extends keyof AnyEntryMap>(
		entry: AnyEntryMap[C][string],
	): Promise<RenderResult>;

	export function reference<C extends keyof AnyEntryMap>(
		collection: C,
	): import('astro/zod').ZodEffects<
		import('astro/zod').ZodString,
		C extends keyof ContentEntryMap
			? {
					collection: C;
					slug: ValidContentEntrySlug<C>;
				}
			: {
					collection: C;
					id: keyof DataEntryMap[C];
				}
	>;
	// Allow generic `string` to avoid excessive type errors in the config
	// if `dev` is not running to update as you edit.
	// Invalid collection names will be caught at build time.
	export function reference<C extends string>(
		collection: C,
	): import('astro/zod').ZodEffects<import('astro/zod').ZodString, never>;

	type ReturnTypeOrOriginal<T> = T extends (...args: any[]) => infer R ? R : T;
	type InferEntrySchema<C extends keyof AnyEntryMap> = import('astro/zod').infer<
		ReturnTypeOrOriginal<Required<ContentConfig['collections'][C]>['schema']>
	>;

	type ContentEntryMap = {
		"articles": {
"christian-mary-or-anne.md": {
	id: "christian-mary-or-anne.md";
  slug: "christian-mary-or-anne";
  body: string;
  collection: "articles";
  data: any
} & { render(): Render[".md"] };
"colonial-medicine.md": {
	id: "colonial-medicine.md";
  slug: "colonial-medicine";
  body: string;
  collection: "articles";
  data: any
} & { render(): Render[".md"] };
"jasper-gunn-arrives.md": {
	id: "jasper-gunn-arrives.md";
  slug: "jasper-gunn-arrives";
  body: string;
  collection: "articles";
  data: any
} & { render(): Render[".md"] };
};
"journal": {
"defence-arrival-1635.md": {
	id: "defence-arrival-1635.md";
  slug: "defence-arrival-1635";
  body: string;
  collection: "journal";
  data: any
} & { render(): Render[".md"] };
"first-people-entries.md": {
	id: "first-people-entries.md";
  slug: "first-people-entries";
  body: string;
  collection: "journal";
  data: any
} & { render(): Render[".md"] };
};
"people": {
"abby-gunn-baker.md": {
	id: "abby-gunn-baker.md";
  slug: "abby-gunn-baker";
  body: string;
  collection: "people";
  data: any
} & { render(): Render[".md"] };
"christian-gunn.md": {
	id: "christian-gunn.md";
  slug: "christian-gunn";
  body: string;
  collection: "people";
  data: any
} & { render(): Render[".md"] };
"jasper-gunn.md": {
	id: "jasper-gunn.md";
  slug: "jasper-gunn";
  body: string;
  collection: "people";
  data: any
} & { render(): Render[".md"] };
"jobamah-gunn-biography.md": {
	id: "jobamah-gunn-biography.md";
  slug: "jobamah-gunn-biography";
  body: string;
  collection: "people";
  data: any
} & { render(): Render[".md"] };
};
"voices": {
"a-little-wayfarer.md": {
	id: "a-little-wayfarer.md";
  slug: "a-little-wayfarer";
  body: string;
  collection: "voices";
  data: any
} & { render(): Render[".md"] };
"abby-gunn-baker-obituary-1923.md": {
	id: "abby-gunn-baker-obituary-1923.md";
  slug: "abby-gunn-baker-obituary-1923";
  body: string;
  collection: "voices";
  data: any
} & { render(): Render[".md"] };
"roosevelt-letter-1908.md": {
	id: "roosevelt-letter-1908.md";
  slug: "roosevelt-letter-1908";
  body: string;
  collection: "voices";
  data: any
} & { render(): Render[".md"] };
};

	};

	type DataEntryMap = {
		"contributions": Record<string, {
  id: string;
  collection: "contributions";
  data: any;
}>;

	};

	type AnyEntryMap = ContentEntryMap & DataEntryMap;

	export type ContentConfig = never;
}
