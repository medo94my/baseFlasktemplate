# using sql alchamy 

### insert
add the data to the table object first 

```python
    user=User(
        name=form.name.data,
        email=form.email.data,
        password=generate_password_hash(form.password.data)
        )
```

to inform data base that we have data to add
```python
    db.session.add(user)
```
we can add data as mutch as we can at this stage but there is no data recorded in database yet

for that we need to commit our action using

```python
db.session.commit()
```

to get back all the recorded data form database

```
tablename.query.all()
```
to get the first result it can find 
```
tablename.query.first()
```
we can also filter the result using (filter_by)
```
tablename.query.filter_by(username='ahmed').all()
```
this will return all the record that have username ahmed in database

to query a user with specific id we use get()

```
tablename.query.get(1)
```

to delete a record
```
tablename = tablename.query.get_or_404(id)
  db.session.delete(tablename)
    db.session.commit()
```

to update

```
tablename = tablename.query.get_or_404(id)
    tablename.title = form.title.data
            tablename.content = form.content.data
            db.session.commit()
```