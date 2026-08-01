import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';

import { ApiError, apiClient } from '../api/client';
import type { DiscussionDetailResponse } from '../api/types';
import { UI_COLORS } from '../constants/colors';
import { useAuth } from '../contexts/AuthContext';
import { openExternalUrl } from '../utils/openExternal';

export default function DiscussDetailScreen() {
  const navigation = useNavigation<any>();
  const postId = Number((useRoute<any>().params || {}).postId);
  const { isAuthenticated, user } = useAuth();
  const [thread, setThread] = useState<DiscussionDetailResponse | null>(null);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setThread(await apiClient.getDiscussion(postId)); }
    catch { setError('This discussion could not load.'); }
    finally { setLoading(false); }
  }, [postId]);
  useEffect(() => { load(); }, [load]);

  const reply = async () => {
    if (!isAuthenticated) { navigation.navigate('Login'); return; }
    const trimmed = body.trim(); if (!trimmed) return;
    setSending(true);
    try { await apiClient.createDiscussionReply(postId, trimmed); setBody(''); await load(); }
    catch (reason) { Alert.alert('Reply not sent', (reason as ApiError)?.status === 429 ? 'Please wait before replying again.' : 'Try again in a moment.'); }
    finally { setSending(false); }
  };
  const report = async () => {
    if (!isAuthenticated) { navigation.navigate('Login'); return; }
    try { await apiClient.reportDiscussionPost(postId); Alert.alert('Report received', 'Thank you. Your report is private.'); }
    catch (reason) { Alert.alert((reason as ApiError)?.status === 409 ? 'Already reported' : 'Report not sent'); }
  };
  const block = async () => {
    const authorId = thread?.author.id;
    if (!isAuthenticated) { navigation.navigate('Login'); return; }
    if (!authorId || authorId === user?.id) return;
    try { await apiClient.blockDiscussionUser(authorId); Alert.alert('Author blocked', 'Their posts will no longer appear for you.'); navigation.goBack(); }
    catch { Alert.alert('Could not block author'); }
  };

  if (loading) return <View style={styles.state}><ActivityIndicator accessibilityLabel="Loading discussion" color={UI_COLORS.ACCENT} /></View>;
  if (error || !thread) return <View style={styles.state} accessibilityRole="alert"><Text style={styles.title}>{error}</Text><Pressable style={styles.primary} onPress={load}><Text style={styles.primaryText}>Try again</Text></Pressable></View>;
  const source = thread.attachments.find((item) => item.type === 'source')?.source;
  return <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <View style={styles.card}><Text style={styles.author}>{thread.author.display_name}</Text><Text style={styles.post}>{thread.body}</Text>
        <View style={styles.actions}>{source ? <Pressable accessibilityRole="link" style={styles.secondary} onPress={() => openExternalUrl(source.url, 'discussion evidence')}><Text style={styles.secondaryText}>View evidence</Text></Pressable> : null}<Pressable accessibilityRole="button" style={styles.secondary} onPress={report}><Text style={styles.secondaryText}>Report</Text></Pressable>{thread.author.id && thread.author.id !== user?.id ? <Pressable accessibilityRole="button" style={styles.secondary} onPress={block}><Text style={styles.secondaryText}>Block author</Text></Pressable> : null}</View>
      </View>
      <Text style={styles.section}>{thread.reply_total} {thread.reply_total === 1 ? 'reply' : 'replies'}</Text>
      {!thread.replies.length ? <Text style={styles.muted}>No replies yet. Start with evidence and explain the tradeoff.</Text> : thread.replies.map((replyItem) => <View key={replyItem.id} style={styles.reply}><Text style={styles.replyAuthor}>{replyItem.author.display_name}</Text><Text style={styles.replyBody}>{replyItem.body}</Text></View>)}
    </ScrollView>
    <View style={styles.composer}><TextInput accessibilityLabel="Write a reply" placeholder={isAuthenticated ? 'Add an evidence-minded reply…' : 'Sign in to reply'} placeholderTextColor={UI_COLORS.TEXT_MUTED} style={styles.input} value={body} onChangeText={setBody} editable={isAuthenticated && !sending} multiline maxLength={10000} /><Pressable accessibilityRole="button" accessibilityState={{ disabled: sending || (isAuthenticated && !body.trim()) }} style={styles.primary} disabled={sending || (isAuthenticated && !body.trim())} onPress={reply}><Text style={styles.primaryText}>{isAuthenticated ? (sending ? 'Sending…' : 'Reply') : 'Sign in'}</Text></Pressable></View>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: UI_COLORS.PRIMARY_BG }, content: { padding: 16, gap: 14, paddingBottom: 28 }, state: { flex: 1, backgroundColor: UI_COLORS.PRIMARY_BG, alignItems: 'center', justifyContent: 'center', gap: 14, padding: 28 },
  card: { backgroundColor: UI_COLORS.CARD_BG, borderRadius: 16, borderWidth: 1, borderColor: UI_COLORS.BORDER, padding: 18, gap: 12 }, author: { color: UI_COLORS.ACCENT, fontWeight: '800' }, post: { color: UI_COLORS.TEXT_PRIMARY, fontSize: 18, lineHeight: 26 },
  title: { color: UI_COLORS.TEXT_PRIMARY, fontSize: 19, fontWeight: '800' }, section: { color: UI_COLORS.TEXT_PRIMARY, fontSize: 16, fontWeight: '800' }, muted: { color: UI_COLORS.TEXT_SECONDARY, lineHeight: 21 },
  reply: { borderLeftWidth: 2, borderLeftColor: UI_COLORS.BORDER_LIGHT, paddingLeft: 14, paddingVertical: 8, gap: 5 }, replyAuthor: { color: UI_COLORS.TEXT_SECONDARY, fontWeight: '700' }, replyBody: { color: UI_COLORS.TEXT_PRIMARY, lineHeight: 21 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, secondary: { borderWidth: 1, borderColor: UI_COLORS.BORDER_LIGHT, borderRadius: 10, minHeight: 44, justifyContent: 'center', paddingHorizontal: 12 }, secondaryText: { color: UI_COLORS.TEXT_SECONDARY, fontWeight: '700' },
  composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: UI_COLORS.BORDER, backgroundColor: UI_COLORS.CARD_BG }, input: { flex: 1, minHeight: 44, maxHeight: 120, borderWidth: 1, borderColor: UI_COLORS.BORDER_LIGHT, borderRadius: 12, color: UI_COLORS.TEXT_PRIMARY, padding: 12 },
  primary: { backgroundColor: UI_COLORS.ACCENT, borderRadius: 10, minHeight: 44, justifyContent: 'center', paddingHorizontal: 16 }, primaryText: { color: UI_COLORS.PRIMARY_BG, fontWeight: '800' },
});
