#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <assert.h>

#define one 10000000
#define dig 7
#define debug 0

int m = 0;

int *h, *u, *v, *l, *se;
int tot = 1; // (simulated) linked lists of adjacent edges; h: heads, (u, v): starting and ending points of an edge, l: pointer to next edge, se: whether edge has been visited, tot: total number of edges ever added
int *s, *ri; // s: whether vertex has been visited, ri: instituion a reviewer belongs to

int *hi, *vi, *li, *si;
int ti=0; // (simulated) linked lists of adjacent institutions; hi: heads, vi: name / number of insitution, li: pointer to next institution, si: whether an institution has been visited at this paper, ti: total number of paper-institution pairs ever added

int *st; 
int top=0, btm=0; // stack for tracking path / cycle to clear; st: stack of pointers, top: top, btm: where path / cycle starts

int *f, *c, *ci;
int fw=0, bw=0; // f: current flow on an edge, c: total load of a vertex (positive for reviewers, negative for papers), ci: total load of a paper-instution pair, (fw, bw): maximum amount of flow that can be added in the forward / backward direction

int* alloc_int(int size)
{
	return (int*) calloc(size, sizeof(int));
}

void alloc_buffers(int vsize, int esize)
{
	h = alloc_int(vsize);
	u = alloc_int(esize);
	v = alloc_int(esize);
	l = alloc_int(esize);
	se = alloc_int(esize);
	s = alloc_int(vsize);
	ri = alloc_int(vsize);
	hi = alloc_int(vsize);
	vi = alloc_int(esize);
	li = alloc_int(esize);
	si = alloc_int(esize);
	st = alloc_int(esize);
	f = alloc_int(esize);
	c = alloc_int(vsize);
	ci = alloc_int(esize);
}

void dealloc_buffers(void) 
{
	free(h);
	free(u);
	free(v);
	free(l);
	free(se);
	free(s);
	free(ri);
	free(hi);
	free(vi);
	free(li);
	free(si);
	free(st);
	free(f);
	free(c);
	free(ci);
}

int min(int a, int b) 
{
	return (a <= b) ? a : b;
}

int fl(int x) // floor
{
    return floor(((double)x) / one) * one;
}

int ce(int x) // ceiling
{
    return ceil(((double)x) / one) * one;
}

int in(int x) // whether a number is ``integral''
{
    return x == fl(x) || x == ce(x);
}
 
void ae(int x, int y, int z) // add an edge from x to y with flow z (and implicitly with capacity 1); also add a co-edge from y to x; note that co-edge of an edge with pointer p has pointer p ^ 1
{
    ++m;
    u[++tot] = x;
    v[tot] = y;
    f[tot] = z;
    l[tot] = h[x];
    h[x] = tot;
}

int fi(int p, int i) // find the pointer at paper p for instution i
{
    for(int j = hi[p]; j; j = li[j])
        if(vi[j] == i) return j;
    return 0;
}

void ai(int p, int i, int w) // add an amount of load, w, to a paper-instution pair (p, i)
{
    int j = fi(p, i);
    if(j)
        ci[j] += w;
    else
    {
        vi[++ti] = i;
        li[ti] = hi[p];
        ci[ti] = w;
        hi[p] = ti;
    }
}

void re(int x) // remove edge with pointer x
{
    --m;
    int t = u[x];
    if(x == h[t])
    {
        h[t] = l[x];
        return;
    }
    int i = h[t];
    while(l[i] != x)
        i = l[i];
    l[i] = l[x];
}

int tr(int x, int i) // find a fractional edge adjacent to x not visited yet belonging to institution i (or any insitution with fractional paper-instituion load when i = 0)
{
    if(!hi[x])
    {
        for(int j = h[x]; j; j = l[j])
            if(!se[j]) return j;
    }
    else if(!i)
    {
        for(int j = hi[x]; j; j = li[j])
            if(!in(ci[j]))
            {
                int t = tr(x, vi[j]);
                if(t) return t;
            }
    }
    else
        for(int j = h[x]; j; j = l[j])
            if(ri[v[j]] == i && !se[j]) return j;
    return 0;
}

void cnr(int x) // if edge with pointer x has flow 0 or 1, then remove it and its co-edge
{
    if(f[x] == 0 || f[x] == one)
    {
        re(x);
        re(x ^ 1);
    }
}

void upd(int x, int y) // add flow y to edge with pointer x; update all load counters associated with the edge
{
    f[x] -= y;
    f[x ^ 1] += y;
    c[u[x]] -= y;
    c[v[x]] += y;

    if(hi[v[x]])
        ai(v[x], ri[u[x]], -y);
    else
        ai(u[x], ri[v[x]], y);

    cnr(x);
}

int go(int x, int y, int p) // x: current vertex, y: previous edge, p: whether finding a path
{
    if(debug) printf("%d %d %d %d\n", x, y, p, top);
    if(y) st[++top] = y; // push incoming edge into stack
    int ret = 0, t = 0, yi = 0, zi = 0;

    if(!hi[x]) // x is a reviewer
    {
        if(debug) printf("c: %d\n", c[x]);
        if(s[x]) // found a cycle
        {
            fw = bw = one;
            btm = 0;

            for(int i = 1; i <= top; i++) // cycle starts from previous edge leaving x
                if(u[st[i]] == x)
                {
                    btm = i;
                    break;
                }

            if(debug) printf("r cycle: %d\n", btm);

            return 1;
        }

        if(y && p && (!in(c[x]))) // found a path
        {
            fw = ce(c[x]) - c[x];
            bw = c[x] - fl(c[x]);
            btm = 1; // path always starts from first edge
            if(debug) printf("r path: %d\n", btm);
            return 1;
        }

        s[x] = 1; // mark reviewer visited
        t = tr(x, 0);

        if(!t) // for some reason no fractional edge is available (should only happen when y = 0)
        {
            if(debug && y) printf("r dead end\n");
            fw = bw = 0;
            return 0;
        }
        if(debug) printf("f[t]: %d\n", f[t]);
        se[t] = se[t ^ 1] = 1; // mark outgoing edge visited
        ret = go(v[t], t, p); // go to next vertex (which should be a paper)
        se[t] = se[t ^ 1] = 0; // and then unmark
        fw = min(fw, f[t]);
        bw = min(bw, f[t ^ 1]);
    }
    else // x is a paper
    {
        yi = fi(x, ri[u[y]]); // set yi to institution of incoming edge

        if(debug) printf("c: %d, ci: %d\n", c[x], ci[yi]);
        
        if(si[yi]) // found an ``even'' cycle (never happens when y = yi = 0)
        {
            fw = bw = one;
            btm = 0;

            for(int i = 1; i <= top; i++)
                if(u[st[i]] == x && ri[v[st[i]]] == vi[yi]) // find first edge in stack (1) leaving x and (2) going to institution of incoming edge -- cycle starts there
                {
                    btm = i;
                    break;
                }

            if(debug) printf("p even cycle: %d\n", btm);
            
            return 1;
        }

        if(s[x] && !in(ci[yi])) // found an ``odd'' cycle
        {
            fw = ci[yi] - fl(ci[yi]);
            bw = ce(ci[yi]) - ci[yi];
            btm = 0;

            int wi = 0;

            for(int i = 1; i <= top; i++) // cycle starts from first edge leaving x which belongs to a fractional institution
                if(u[st[i]] == x)
                {
                    wi = fi(x, ri[v[st[i]]]);
                    if(!in(ci[wi]))
                    {
                        btm = i;
                        break;
                    }
                }

            fw = min(fw, ce(ci[wi]) - ci[wi]);
            bw = min(bw, ci[wi] - fl(ci[wi]));

            if(debug) printf("p odd cycle: %d\n", btm);

            return 1;
        }

        if(y && p && (!in(c[x])) && (!in(ci[yi]))) // found a path
        {
            fw = ce(c[x]) - c[x];
            bw = c[x] - fl(c[x]);
            fw = min(fw, ci[yi] - fl(ci[yi]));
            bw = min(bw, ce(ci[yi]) - ci[yi]);
            btm = 1; // path always starts from first edge
            if(debug) printf("p path: %d\n", btm);
            return 1;
        }
    
        if(in(ci[yi])) // integral institution load -- leave through the same institution (equivalent to the other case when y = yi = 0)
            t = tr(x, vi[yi]);
        else // leave through any fractional institution
            t = tr(x, 0);

        if(!t) // should only happen when y = 0
        {
            fw = bw = 0;
            if(debug && y) printf("p dead end\n");
            return 0;
        }

        if(debug) printf("f[t]: %d\n", f[t]);

        zi = fi(x, ri[v[t]]); // set zi to instituion of outgoing edge
        si[zi] = 1; // mark paper-instution pair visited
        se[t] = se[t ^ 1] = 1; // mark edge visited
        if(!in(ci[zi])) s[x] = 1; // and if leaving through a fractional instituion -- mark vertex visited

        ret = go(v[t], t, p); // go to next vertex (which should be a reviewer)

        si[zi] = 0; // unmark institution
        se[t] = se[t ^ 1] = 0; // and unmark edge

        fw = min(fw, f[t]);
        bw = min(bw, f[t ^ 1]);
        
        
    }

    if(t == st[btm] && fw + bw != 0) // if path / cycle starts from current edge, clear path / cycle
    {
        if((!y) && p) // it's a path
        {
            fw = min(fw, c[x] - fl(c[x]));
            bw = min(bw, ce(c[x]) - c[x]);
            if(hi[x]) // need to consider load of paper-insitution pair of outgoing edge too
            {
                int yi = fi(x, ri[v[t]]);
                fw = min(fw, ce(ci[yi]) - ci[yi]);
                bw = min(bw, ci[yi] - fl(ci[yi]));
            }
        }
        if(debug) printf("clearing a path/cycle: %d %d\n", fw, bw);
        int r, d;
        if(((double)rand()) / RAND_MAX < ((double)bw) / (fw + bw)) // update forward wp bw / (fw + bw), etc
        {
            d = 1;
            r = fw;
        }
        else
        {
            d = -1;
            r = bw;
        }

        for(int i = btm; i <= top; i++) upd(st[i], r * d); // update every edge on path / cycle
        fw = bw = 0;
    }

    if(hi[x] && yi != zi) // this part of update must happen after clearing cycle / path
    {
        fw = min(fw, ce(ci[zi]) - ci[zi]);
        bw = min(bw, ci[zi] - fl(ci[zi]));

        fw = min(fw, ci[yi] - fl(ci[yi]));
        bw = min(bw, ce(ci[yi]) - ci[yi]);
    }

    return ret;
}

// reviewer number, starting at 1
int idx_to_rev(int i, int npaps, int nrevs)
{
	return (i % nrevs) + 1;
}

// paper number, padded by nrevs and starting at 1
int idx_to_pap(int i, int npaps, int nrevs)
{
	return ((int) (i / nrevs)) + nrevs + 1;
}

// starting at 0
int pap_rev_to_idx(int p, int r, int npaps, int nrevs)
{
	return ((p - nrevs - 1) * nrevs) + (r - 1);
}

// flows is row-major flattened matrix of papers by reviewers
int run_bvn(double* flows, int* subsets, int npaps, int nrevs)
{
    srand(time(0)); // set random seed to current time
    rand(); // throw away first random number

    int n = npaps + nrevs;

	// carefully round flows to integers to preserve sums
	int* trunc_flows = (int*) malloc((nrevs * npaps) * sizeof(int));
	int* res = (int*) calloc(n + 1, sizeof(int));
	double* sums = (double*) calloc(n + 1, sizeof(double));
	for(int i = 0; i < npaps*nrevs; i++)
	{
		int x = idx_to_rev(i, npaps, nrevs);
		int y = idx_to_pap(i, npaps, nrevs);
		int z = (int) (flows[i] * one); // truncated integer flow
		trunc_flows[i] = z;
		res[x] += trunc_flows[i];
		res[y] += trunc_flows[i];
		sums[x] += flows[i];
		sums[y] += flows[i];
	}
	for(int i = 1; i <= n; i++)
	{
		res[i] = (one * round(sums[i])) - res[i];
	}
	for(int i = 0; i < npaps*nrevs; i++)
	{
		int x = idx_to_rev(i, npaps, nrevs);
		int y = idx_to_pap(i, npaps, nrevs);
		int to_add = min(res[x], res[y]);
		trunc_flows[i] += to_add;
		res[x] -= to_add;
		res[y] -= to_add;
	}
	free(res);
	free(sums);


	// allocate space for n vertices, and 2*p*r maximum edges
	alloc_buffers(n + 1, (2 * npaps * nrevs) + 1);

    for(int i = 1; i <= nrevs; i++) ri[i] = subsets[i-1];//scanf("%d", &ri[i]);

    for(int i = 0; i < npaps*nrevs; i++)
    {
		int x = idx_to_rev(i, npaps, nrevs);
		int y = idx_to_pap(i, npaps, nrevs);
		int z = trunc_flows[i];

        c[x] += z; // update load counters at vertices
        c[y] -= z;
        if(z != 0) // if flow is nonzero, add edge
        {
            ae(x, y, z);
            ae(y, x, one - z);

            ai(y, ri[x], z); // and update flow counter for paper-institution pair

            cnr(tot); // remove edge if flow is already integral
        }

    }
	free(trunc_flows);

    while(m) // while there are still fractional edges left
    {
        if(debug) printf("%d\n", m);
        memset(s, 0, (n + 1) * sizeof(int)); // mark all vertices unvisited
        for(int i = 1; i <= n; i++) // try to find paths / cycles starting from vertices with fractional load
            if(!in(c[i]))
            {
                top = 0;
                if(go(i, 0, 1)) break;
            }

        memset(s, 0, (n + 1) * sizeof(int)); // mark all vertices unvisited
        for(int i = 1; i <= n; i++) // now try to find cycles only starting from all vertices
        {
            top = 0;
            if(go(i, 0, 0)) break;
        }
    }

	// set all flows to 0 for output
    for(int i = 0; i < npaps * nrevs; i++)
    {
		flows[i] = 0;
	}

    for(int i = 2; i <= tot; i++) 
	{
        if(u[i] < v[i] && f[i] == one) // output all edges whose final flow is one -- these constitute the integral matching
		{
			//int x = u[i] - 1;
			//int y = v[i] - 1 - nrevs;
			//flows[(x * npaps) + y] = 1;
			int idx = pap_rev_to_idx(v[i], u[i], npaps, nrevs);
			flows[idx] = 1;
		}
	}

	dealloc_buffers();
    return 0;
}


int main(void) {

	double flows[8];
	for (int i = 0; i < 8; i++) flows[i] = 0.5;
	int ss[4];
	for (int i = 0; i < 4; i++) ss[i] = 1;

	run_bvn(flows, ss, 2, 4);
}
