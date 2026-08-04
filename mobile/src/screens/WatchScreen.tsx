import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  AppState,
  FlatList,
  Pressable,
  Share,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
  ViewToken,
} from 'react-native';
import { useIsFocused, useNavigation } from '@react-navigation/native';
import { useVideoPlayer, VideoView } from 'expo-video';
import * as Clipboard from 'expo-clipboard';

import { apiClient } from '../api/client';
import type { WatchVideo } from '../api/types';
import { openExternalUrl } from '../utils/openExternal';

function WatchCard({ item, active, reducedMotion }: { item: WatchVideo; active: boolean; reducedMotion: boolean }) {
  const navigation = useNavigation<any>();
  const officialEmbed = item.delivery?.mode === 'official_embed' ? item.delivery : null;
  const linkOut = item.delivery?.mode === 'link_out' ? item.delivery : officialEmbed;
  const [transcriptVisible, setTranscriptVisible] = useState(true);
  const [mediaUnavailable, setMediaUnavailable] = useState(false);
  const [shareStatus, setShareStatus] = useState('');
  const player = useVideoPlayer(linkOut ? null : item.media_url, (instance) => {
    instance.loop = true;
    instance.muted = false;
  });

  useEffect(() => {
    const subscription = player.addListener('statusChange', ({ status }) => {
      if (status === 'error') setMediaUnavailable(true);
    });
    return () => subscription.remove();
  }, [player]);

  useEffect(() => {
    if (active && !reducedMotion && !mediaUnavailable && !linkOut) player.play();
    else player.pause();
  }, [active, reducedMotion, mediaUnavailable, linkOut, player]);

  const shareVideo = async () => {
    setShareStatus('Opening share options…');
    try {
      const preview = await apiClient.getVideoSharePreview(item.video_id);
      await Share.share({ title: preview.title, message: `${preview.description}\n${preview.canonical_url}`, url: preview.canonical_url });
      setShareStatus('Share options opened.');
    } catch {
      setShareStatus('Could not open share options. Try again.');
    }
  };

  const copyVideoLink = async () => {
    setShareStatus('Copying link…');
    try {
      const preview = await apiClient.getVideoSharePreview(item.video_id);
      await Clipboard.setStringAsync(preview.canonical_url);
      setShareStatus('Link copied.');
    } catch {
      setShareStatus('Could not copy the link. Try again.');
    }
  };

  return (
    <View style={styles.card} accessible accessibilityLabel={`${item.creator_label}. ${item.caption}`}>
      {linkOut ? (
        <View style={styles.unavailable}>
          <Text style={styles.unavailableTitle}>Watch at the official source</Text>
          <Text style={styles.body}>This provider opens in your browser. The transcript and civic context remain available here.</Text>
          <Pressable accessibilityRole="link" style={styles.button} onPress={() => openExternalUrl(linkOut.canonical_url, linkOut.source_label ?? 'official video source')}>
            <Text style={styles.buttonText}>Open official video</Text>
          </Pressable>
        </View>
      ) : !mediaUnavailable ? (
        <VideoView
          style={StyleSheet.absoluteFill}
          player={player}
          nativeControls={false}
          contentFit="cover"
          accessibilityLabel="Housing and Rent civic video"
          onFirstFrameRender={() => setMediaUnavailable(false)}
        />
      ) : (
        <View style={styles.unavailable} accessibilityRole="alert">
          <Text style={styles.unavailableTitle}>Video unavailable</Text>
          <Text style={styles.body}>The evidence and transcript are still available.</Text>
        </View>
      )}
      <View style={styles.scrim} pointerEvents="none" />
      <View style={styles.overlay}>
        <Text style={styles.creator}>{item.creator_label}</Text>
        <Text style={styles.caption}>{item.caption}</Text>
        {transcriptVisible && item.transcript ? (
          <Text style={styles.transcript} accessibilityLiveRegion="polite">{item.transcript}</Text>
        ) : null}
        <Text style={styles.timestamp}>{new Date(item.published_at).toLocaleDateString()}</Text>
        <View style={styles.actions}>
          <Pressable accessibilityRole="button" accessibilityLabel="Share this civic video" style={styles.button} onPress={shareVideo}>
            <Text style={styles.buttonText}>Share</Text>
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel="Copy link to this civic video" style={styles.button} onPress={copyVideoLink}>
            <Text style={styles.buttonText}>Copy link</Text>
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel="Discuss this civic video" style={styles.discussButton} onPress={() => item.discussion_post_id ? navigation.navigate('DiscussTab', { screen: 'DiscussDetail', params: { postId: item.discussion_post_id, returnToVideoId: item.video_id } }) : navigation.navigate('DiscussTab')}>
            <Text style={styles.discussButtonText}>Discuss</Text>
          </Pressable>
          <Pressable accessibilityRole="button" style={styles.button} onPress={() => openExternalUrl(item.source.url, 'evidence source')}>
            <Text style={styles.buttonText}>Evidence</Text>
          </Pressable>
          <Pressable accessibilityRole="link" style={styles.button} onPress={() => openExternalUrl('https://wethepeople.place/issues/housing-rent', 'Housing and Rent issue')}>
            <Text style={styles.buttonText}>{item.issue.title}</Text>
          </Pressable>
          {item.bills[0] ? (
            <Pressable accessibilityRole="link" style={styles.button} onPress={() => openExternalUrl(`https://www.congress.gov/bill/119th-congress/house-bill/${item.bills[0].bill_id.match(/\d+/)?.[0] ?? '1'}`, 'related bill')}>
              <Text style={styles.buttonText}>{item.bills[0].bill_id.toUpperCase()}</Text>
            </Pressable>
          ) : null}
          <Pressable accessibilityRole="button" accessibilityState={{ checked: transcriptVisible }} style={styles.button} onPress={() => setTranscriptVisible((value) => !value)}>
            <Text style={styles.buttonText}>Transcript {transcriptVisible ? 'shown' : 'hidden'}</Text>
          </Pressable>
          {!linkOut && (reducedMotion || mediaUnavailable) && (
            <Pressable accessibilityRole="button" style={styles.button} onPress={() => { setMediaUnavailable(false); player.play(); }}>
              <Text style={styles.buttonText}>Play video</Text>
            </Pressable>
          )}
        </View>
        {shareStatus ? <Text accessibilityLiveRegion="polite" style={styles.shareStatus}>{shareStatus}</Text> : null}
      </View>
    </View>
  );
}

export default function WatchScreen() {
  const { height } = useWindowDimensions();
  const focused = useIsFocused();
  const [videos, setVideos] = useState<WatchVideo[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [appActive, setAppActive] = useState(AppState.currentState === 'active');
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    apiClient.getWatchVideos({ limit: 10 }, { signal: controller.signal })
      .then((result) => {
        setVideos(result.videos);
        setActiveId(result.videos[0]?.video_id ?? null);
        setNextCursor(result.next_cursor);
        setHasMore(result.has_more);
      })
      .catch((reason) => { if (reason?.name !== 'AbortError') setError('Watch could not load.'); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const loadMore = useCallback(() => {
    if (!hasMore || !nextCursor || loadingMore) return;
    setLoadingMore(true);
    apiClient.getWatchVideos({ cursor: nextCursor, limit: 10 })
      .then((result) => {
        setVideos((current) => {
          const known = new Set(current.map((item) => item.video_id));
          return [...current, ...result.videos.filter((item) => !known.has(item.video_id))];
        });
        setNextCursor(result.next_cursor);
        setHasMore(result.has_more);
      })
      .catch(() => setError('More Watch videos could not load.'))
      .finally(() => setLoadingMore(false));
  }, [hasMore, nextCursor, loadingMore]);

  useEffect(load, [load]);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion);
    const motion = AccessibilityInfo.addEventListener('reduceMotionChanged', setReducedMotion);
    const state = AppState.addEventListener('change', (next) => setAppActive(next === 'active'));
    return () => { motion.remove(); state.remove(); };
  }, []);

  const onViewableItemsChanged = useRef(({ viewableItems }: { viewableItems: ViewToken<WatchVideo>[] }) => {
    const visible = viewableItems.find((token) => token.isViewable);
    setActiveId(visible?.item.video_id ?? null);
  }).current;

  if (loading) return <View style={styles.center}><ActivityIndicator accessibilityLabel="Loading Watch" color="#fff" /><Text style={styles.body}>Loading Watch…</Text></View>;
  if (error) return <View style={styles.center} accessibilityRole="alert"><Text style={styles.unavailableTitle}>{error}</Text><Pressable style={styles.button} onPress={load}><Text style={styles.buttonText}>Retry</Text></Pressable></View>;
  if (!videos.length) return <View style={styles.center}><Text style={styles.unavailableTitle}>No videos yet</Text><Text style={styles.body}>Curated civic videos will appear here.</Text></View>;

  return (
    <FlatList
      accessibilityLabel="Watch civic videos"
      data={videos}
      keyExtractor={(item) => item.video_id}
      renderItem={({ item }) => <View style={{ height }}><WatchCard item={item} active={focused && appActive && activeId === item.video_id} reducedMotion={reducedMotion} /></View>}
      pagingEnabled
      keyboardShouldPersistTaps="handled"
      initialNumToRender={1}
      maxToRenderPerBatch={2}
      windowSize={3}
      viewabilityConfig={{ itemVisiblePercentThreshold: 60 }}
      onViewableItemsChanged={onViewableItemsChanged}
      onEndReached={loadMore}
      onEndReachedThreshold={0.5}
      ListFooterComponent={loadingMore ? <ActivityIndicator accessibilityLabel="Loading more Watch videos" color="#fff" /> : null}
    />
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, backgroundColor: '#070B14' },
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.30)' },
  overlay: { flex: 1, justifyContent: 'flex-end', padding: 24, paddingBottom: 88 },
  creator: { color: '#fff', fontSize: 18, fontWeight: '800', marginBottom: 8 },
  caption: { color: '#fff', fontSize: 17, lineHeight: 24 },
  transcript: { color: '#fff', backgroundColor: 'rgba(0,0,0,0.72)', padding: 10, marginTop: 12, lineHeight: 20 },
  timestamp: { color: '#D1D5DB', marginTop: 8 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 },
  button: { backgroundColor: '#fff', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 10, minHeight: 44, justifyContent: 'center' },
  buttonText: { color: '#111827', fontWeight: '700' },
  discussButton: { backgroundColor: '#C5A044', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, minHeight: 44, justifyContent: 'center' },
  discussButtonText: { color: '#0A0F1A', fontWeight: '800' },
  center: { flex: 1, backgroundColor: '#070B14', alignItems: 'center', justifyContent: 'center', gap: 16, padding: 24 },
  unavailable: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center', padding: 24 },
  unavailableTitle: { color: '#fff', fontSize: 22, fontWeight: '800', textAlign: 'center' },
  body: { color: '#D1D5DB', textAlign: 'center' },
  shareStatus: { color: '#fff', marginTop: 10, fontSize: 13 },
});
