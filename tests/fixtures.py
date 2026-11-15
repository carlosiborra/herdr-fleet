def agent(pane='w1:p1', status='working', workspace='w1', tab='w1:t1',
          title='Implement API', kind='codex', seq=1, session='session-a'):
    return dict(agent=kind, agent_status=status, workspace_id=workspace,
                tab_id=tab, pane_id=pane, terminal_title_stripped=title,
                cwd='/example/project', focused=False, state_change_seq=seq,
                completion_seq=seq if status == 'done' else None,
                agent_session={'id': session})


def fleet():
    return [agent(), agent('w1:p2', 'done', title='Review Unicode 界 café', kind='claude'),
            agent('w1:p3', 'idle', tab='w1:t2', title='Awaiting task'),
            agent('w2:p1', 'working', 'w2', 'w2:t1', 'Long title ' * 15),
            agent('w2:p2', 'blocked', 'w2', 'w2:t1', 'Approval required'),
            agent('w3:p1', 'unknown', 'w3', 'w3:t1', 'Unclassified')]
