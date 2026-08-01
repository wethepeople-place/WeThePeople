import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import { apiClient } from '../api/client';
import type { DiscussionPost } from '../api/types';
import { UI_COLORS } from '../constants/colors';

export default function DiscussFeedScreen() {
  const navigation = useNavigation<any>();
  const [items, setItems] = useState<DiscussionPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError(null);
    try { setItems((await apiClient.getDiscussions()).items); }
    catch { setError('Discussions could not load.'); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  if (loading) return <State><ActivityIndicator accessibilityLabel="Loading discussions" color={UI_COLORS.ACCENT} /><Text style={styles.muted}>Loading discussions…</Text></State>;
  if (error) return <State alert><Text style={styles.title}>{error}</Text><Pressable style={styles.primary} onPress={() => load()}><Text style={styles.primaryText}>Try again</Text></Pressable></State>;
  if (!items.length) return <State><Text style={styles.title}>No discussions yet</Text><Text style={styles.muted}>Curated civic conversations will appear here.</Text></State>;

  return <FlatList
    accessibilityLabel="Civic discussion feed"
    style={styles.screen}
    contentContainerStyle={styles.list}
    data={items}
    keyExtractor={(item) => String(item.id)}
    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={UI_COLORS.ACCENT} />}
    renderItem={({ item }) => <Pressable accessibilityRole="button" accessibilityLabel={`Open discussion by ${item.author.display_name}`} style={styles.card} onPress={() => navigation.navigate('DiscussDetail', { postId: item.id })}>
      <Text style={styles.author}>{item.author.display_name}</Text>
      <Text style={styles.body}>{item.body}</Text>
      <View style={styles.attachments}>{item.attachments.map((attachment) => <View key={`${attachment.type}-${attachment.reference_id}`} style={styles.chip}><Text style={styles.chipText}>{attachment.label || attachment.type}</Text></View>)}</View>
      <Text style={styles.meta}>{item.reply_count} {item.reply_count === 1 ? 'reply' : 'replies'} · {new Date(item.created_at).toLocaleDateString()}</Text>
    </Pressable>}
  />;
}

function State({ children, alert = false }: { children: React.ReactNode; alert?: boolean }) {
  return <View style={styles.state} accessibilityRole={alert ? 'alert' : undefined}>{children}</View>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: UI_COLORS.PRIMARY_BG }, list: { padding: 16, gap: 12 },
  state: { flex: 1, backgroundColor: UI_COLORS.PRIMARY_BG, alignItems: 'center', justifyContent: 'center', gap: 14, padding: 28 },
  card: { backgroundColor: UI_COLORS.CARD_BG, borderWidth: 1, borderColor: UI_COLORS.BORDER, borderRadius: 16, padding: 18, gap: 10 },
  author: { color: UI_COLORS.ACCENT, fontWeight: '800', fontSize: 15 }, title: { color: UI_COLORS.TEXT_PRIMARY, fontSize: 19, fontWeight: '800', textAlign: 'center' },
  body: { color: UI_COLORS.TEXT_PRIMARY, fontSize: 16, lineHeight: 23 }, muted: { color: UI_COLORS.TEXT_SECONDARY, textAlign: 'center' }, meta: { color: UI_COLORS.TEXT_MUTED, fontSize: 12 },
  attachments: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 }, chip: { backgroundColor: UI_COLORS.GOLD_LIGHT, borderRadius: 12, paddingHorizontal: 9, paddingVertical: 5 }, chipText: { color: UI_COLORS.ACCENT, fontSize: 11, fontWeight: '700' },
  primary: { backgroundColor: UI_COLORS.ACCENT, borderRadius: 10, minHeight: 44, justifyContent: 'center', paddingHorizontal: 18 }, primaryText: { color: UI_COLORS.PRIMARY_BG, fontWeight: '800' },
});
