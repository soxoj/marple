## Maigret Exporter

Run Marple with the folloing parameters to export new sites to Maigret:

```
python3 marple.py text --plugins maigret extract_username maigret_export random_username
```

### TODO

- [ ] Add an direct integration with Maigret (`--submit`)
- [ ] Implement the GitHub API call to create an issue with parameters of a new site
- [ ] Utilize AI to determine if a link is similar to an account page
- [ ] Add a generation of tags for a website with AI
